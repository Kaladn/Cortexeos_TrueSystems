use std::env;
use std::fs::{create_dir_all, File};
use std::io::{BufWriter, Write};
use std::os::fd::{AsRawFd, OwnedFd};
use std::path::PathBuf;
use std::thread::sleep;
use std::time::{Duration, Instant};
use ashpd::desktop::screencast::{
    CursorMode, Screencast, SelectSourcesOptions, SourceType, Stream,
};
use gstreamer as gst;
use gstreamer::prelude::*;
use gstreamer_app as gst_app;
use gstreamer_video as gst_video;

const FEATURE_NAMES: [&str; 16] = [
    "rgb_mean_r",
    "rgb_mean_g",
    "rgb_mean_b",
    "rgb_std_r",
    "rgb_std_g",
    "rgb_std_b",
    "hsv_mean_h",
    "hsv_mean_s",
    "hsv_mean_v",
    "luma_mean",
    "luma_std",
    "saturation_mean",
    "delta_luma_abs",
    "edge_density",
    "texture_energy",
    "motion_energy",
];

#[derive(Clone)]
struct Args {
    duration: f64,
    fps: f64,
    resolution: (usize, usize),
    grid: (usize, usize),
    region: Option<(i32, i32, i32, i32)>,
    output_root: PathBuf,
    run_id: String,
    start_delay: f64,
    chunk_frames: usize,
}

struct CaptureContext {
    pipeline: gst::Pipeline,
    sink: gst_app::AppSink,
    width: usize,
    height: usize,
}

impl Drop for CaptureContext {
    fn drop(&mut self) {
        let _ = self.pipeline.set_state(gst::State::Null);
    }
}

#[tokio::main]
async fn main() {
    if let Err(error) = run().await {
        eprintln!("{error}");
        std::process::exit(1);
    }
}

async fn run() -> Result<(), String> {
    let args = parse_args()?;
    if args.resolution.0 % args.grid.0 != 0 || args.resolution.1 % args.grid.1 != 0 {
        return Err("resolution must divide evenly by grid".to_string());
    }
    if args.start_delay > 0.0 {
        println!(
            "Starting native capture in {:.3} seconds.",
            args.start_delay
        );
        sleep(Duration::from_secs_f64(args.start_delay));
    }

    let run_dir = args.output_root.join(&args.run_id);
    let cell_dir = run_dir.join("cell_state_native");
    create_dir_all(&cell_dir).map_err(|e| format!("create run dir failed: {e}"))?;

    let records_path = run_dir.join(format!("{}_records.jsonl", args.run_id));
    let mut records = BufWriter::new(
        File::create(&records_path).map_err(|e| format!("records open failed: {e}"))?,
    );

    gst::init().map_err(|e| format!("GStreamer initialization failed: {e}"))?;
    let (portal, session, stream, remote_fd) = open_portal().await?;
    let source_region = source_region(&args, &stream);
    let ctx = CaptureContext::new(&args, source_region, &stream, &remote_fd)?;
    let mut bgra = vec![0_u8; args.resolution.0 * args.resolution.1 * 4];
    let mut previous_luma = vec![0_f32; args.grid.0 * args.grid.1];
    let mut have_previous = false;

    let mut chunk_frames: Vec<f32> =
        Vec::with_capacity(args.chunk_frames * args.grid.0 * args.grid.1 * FEATURE_NAMES.len());
    let mut chunk_numbers: Vec<u32> = Vec::with_capacity(args.chunk_frames);
    let mut chunks: Vec<ChunkMeta> = Vec::new();

    let started = Instant::now();
    let mut frame_number: u32 = 0;
    while started.elapsed().as_secs_f64() < args.duration {
        let frame_started = Instant::now();
        ctx.capture(source_region, &mut bgra)?;
        let screen_energy = build_cell_state(
            &bgra,
            &args,
            &mut previous_luma,
            &mut have_previous,
            &mut chunk_frames,
        );
        chunk_numbers.push(frame_number);

        let elapsed = started.elapsed().as_secs_f64();
        writeln!(
            records,
            "{{\"schema_version\":1,\"record_kind\":\"truevision_native_rs_frame_state\",\"run_id\":\"{}\",\"observed_at_utc\":\"{}\",\"frame_number\":{},\"elapsed_seconds\":{:.6},\"fps\":{},\"screen_energy\":{:.3},\"raw_frame_saved\":false,\"raw_grid_saved\":false}}",
            json_escape(&args.run_id),
            utc_timestamp(),
            frame_number,
            elapsed,
            args.fps,
            screen_energy
        )
        .map_err(|e| format!("records write failed: {e}"))?;

        if chunk_numbers.len() >= args.chunk_frames {
            flush_chunk(
                &args,
                &cell_dir,
                &mut chunks,
                &mut chunk_frames,
                &mut chunk_numbers,
            )?;
        }

        frame_number += 1;
        let target = Duration::from_secs_f64(1.0 / args.fps.max(0.001));
        let spent = frame_started.elapsed();
        if spent < target {
            sleep(target - spent);
        }
    }
    flush_chunk(
        &args,
        &cell_dir,
        &mut chunks,
        &mut chunk_frames,
        &mut chunk_numbers,
    )?;
    records
        .flush()
        .map_err(|e| format!("records flush failed: {e}"))?;

    let duration_seconds = started.elapsed().as_secs_f64();
    write_summary(
        &args,
        &run_dir,
        frame_number,
        duration_seconds,
        source_region,
    )?;
    write_manifest(
        &args,
        &run_dir,
        &records_path,
        &chunks,
        frame_number,
        duration_seconds,
        source_region,
    )?;

    println!(
        "{{\n  \"run_id\": \"{}\",\n  \"frames\": {},\n  \"duration_seconds\": {:.3},\n  \"run_dir\": \"{}\",\n  \"records_jsonl\": \"{}\",\n  \"summary_json\": \"{}\",\n  \"manifest_json\": \"{}\"\n}}",
        json_escape(&args.run_id),
        frame_number,
        duration_seconds,
        json_escape(&run_dir.display().to_string()),
        json_escape(&records_path.display().to_string()),
        json_escape(&run_dir.join(format!("{}_summary.json", args.run_id)).display().to_string()),
        json_escape(&run_dir.join(format!("{}_manifest.json", args.run_id)).display().to_string()),
    );
    drop(ctx);
    drop(remote_fd);
    drop(session);
    drop(portal);
    Ok(())
}

async fn open_portal() -> Result<(
    Screencast,
    ashpd::desktop::Session<Screencast>,
    Stream,
    OwnedFd,
), String> {
    let portal = Screencast::new()
        .await
        .map_err(|e| format!("ScreenCast portal unavailable: {e}"))?;
    let session = portal
        .create_session(Default::default())
        .await
        .map_err(|e| format!("ScreenCast session creation failed: {e}"))?;
    portal
        .select_sources(
            &session,
            SelectSourcesOptions::default()
                .set_cursor_mode(CursorMode::Embedded)
                .set_sources(enumflags2::BitFlags::from_flag(SourceType::Monitor))
                .set_multiple(false)
                .set_persist_mode(ashpd::desktop::PersistMode::DoNot),
        )
        .await
        .map_err(|e| format!("ScreenCast source selection failed: {e}"))?
        .response()
        .map_err(|e| format!("ScreenCast source configuration was rejected: {e}"))?;
    let response = portal
        .start(&session, None, Default::default())
        .await
        .map_err(|e| format!("ScreenCast start request failed: {e}"))?
        .response()
        .map_err(|e| format!("ScreenCast source was not admitted: {e}"))?;
    let stream = response
        .streams()
        .first()
        .cloned()
        .ok_or_else(|| "ScreenCast portal returned no selected stream".to_string())?;
    let remote_fd = portal
        .open_pipe_wire_remote(&session, Default::default())
        .await
        .map_err(|e| format!("PipeWire remote open failed: {e}"))?;
    Ok((portal, session, stream, remote_fd))
}

impl CaptureContext {
    fn new(args: &Args, region: (i32, i32, i32, i32), stream: &Stream, remote_fd: &OwnedFd) -> Result<Self, String> {
        let (source_width, source_height) = stream
            .size()
            .unwrap_or((region.0 + region.2, region.1 + region.3));
        let crop_right = (source_width - region.0 - region.2).max(0);
        let crop_bottom = (source_height - region.1 - region.3).max(0);
        let source = gst::ElementFactory::make("pipewiresrc")
            .property("fd", remote_fd.as_raw_fd())
            .property("path", stream.pipe_wire_node_id().to_string())
            .build()
            .map_err(|e| format!("PipeWire source creation failed: {e}"))?;
        let convert = gst::ElementFactory::make("videoconvert").build().map_err(|e| format!("video conversion creation failed: {e}"))?;
        let scale = gst::ElementFactory::make("videoscale").build().map_err(|e| format!("video scaling creation failed: {e}"))?;
        let caps = gst::Caps::builder("video/x-raw")
            .field("format", "BGRA")
            .field("width", args.resolution.0 as i32)
            .field("height", args.resolution.1 as i32)
            .build();
        let sink = gst_app::AppSink::builder()
            .caps(&caps)
            .max_buffers(1)
            .drop(true)
            .sync(false)
            .build();
        let pipeline = gst::Pipeline::new();
        if args.region.is_some() {
            let crop = gst::ElementFactory::make("videocrop")
                .property("left", region.0)
                .property("top", region.1)
                .property("right", crop_right)
                .property("bottom", crop_bottom)
                .build()
                .map_err(|e| format!("explicit --region requires the Linux GStreamer videocrop element: {e}"))?;
            pipeline.add_many([&source, &crop, &convert, &scale, sink.upcast_ref()]).map_err(|e| format!("capture pipeline assembly failed: {e}"))?;
            gst::Element::link_many([&source, &crop, &convert, &scale, sink.upcast_ref()]).map_err(|e| format!("capture pipeline link failed: {e}"))?;
        } else {
            pipeline.add_many([&source, &convert, &scale, sink.upcast_ref()]).map_err(|e| format!("capture pipeline assembly failed: {e}"))?;
            gst::Element::link_many([&source, &convert, &scale, sink.upcast_ref()]).map_err(|e| format!("capture pipeline link failed: {e}"))?;
        }
        pipeline.set_state(gst::State::Playing).map_err(|e| format!("capture pipeline start failed: {e}"))?;
        Ok(Self { pipeline, sink, width: args.resolution.0, height: args.resolution.1 })
    }

    fn capture(&self, _region: (i32, i32, i32, i32), out_bgra: &mut [u8]) -> Result<(), String> {
        let sample = self.sink.try_pull_sample(gst::ClockTime::from_seconds(3)).ok_or_else(|| "PipeWire frame timed out".to_string())?;
        let caps = sample.caps().ok_or_else(|| "PipeWire frame has no negotiated caps".to_string())?;
        let info = gst_video::VideoInfo::from_caps(caps).map_err(|e| format!("PipeWire video format unavailable: {e}"))?;
        let stride = info.stride()[0] as usize;
        let buffer = sample.buffer().ok_or_else(|| "PipeWire sample has no buffer".to_string())?;
        let map = buffer.map_readable().map_err(|_| "PipeWire frame mapping failed".to_string())?;
        let row_bytes = self.width * 4;
        if map.len() < stride * self.height || out_bgra.len() < row_bytes * self.height {
            return Err("PipeWire frame buffer is smaller than negotiated geometry".to_string());
        }
        for row in 0..self.height {
            out_bgra[row * row_bytes..(row + 1) * row_bytes]
                .copy_from_slice(&map[row * stride..row * stride + row_bytes]);
        }
        Ok(())
    }
}

fn build_cell_state(
    bgra: &[u8],
    args: &Args,
    previous_luma: &mut [f32],
    have_previous: &mut bool,
    output: &mut Vec<f32>,
) -> f32 {
    let (width, height) = args.resolution;
    let (grid_w, grid_h) = args.grid;
    let cell_w = width / grid_w;
    let cell_h = height / grid_h;
    let pixels_per_cell = (cell_w * cell_h) as f32;
    let mut screen_energy = 0.0_f32;

    for gy in 0..grid_h {
        for gx in 0..grid_w {
            let mut sum_r = 0.0_f32;
            let mut sum_g = 0.0_f32;
            let mut sum_b = 0.0_f32;
            let mut sum_r2 = 0.0_f32;
            let mut sum_g2 = 0.0_f32;
            let mut sum_b2 = 0.0_f32;
            let mut sum_l = 0.0_f32;
            let mut sum_l2 = 0.0_f32;
            let mut sum_sat = 0.0_f32;
            let mut sum_v = 0.0_f32;

            for y in (gy * cell_h)..((gy + 1) * cell_h) {
                let row = y * width * 4;
                for x in (gx * cell_w)..((gx + 1) * cell_w) {
                    let idx = row + x * 4;
                    let b = bgra[idx] as f32;
                    let g = bgra[idx + 1] as f32;
                    let r = bgra[idx + 2] as f32;
                    let maxc = r.max(g).max(b);
                    let minc = r.min(g).min(b);
                    let sat = if maxc > 0.0 {
                        ((maxc - minc) / maxc) * 255.0
                    } else {
                        0.0
                    };
                    let luma = 0.299 * r + 0.587 * g + 0.114 * b;
                    sum_r += r;
                    sum_g += g;
                    sum_b += b;
                    sum_r2 += r * r;
                    sum_g2 += g * g;
                    sum_b2 += b * b;
                    sum_l += luma;
                    sum_l2 += luma * luma;
                    sum_sat += sat;
                    sum_v += maxc;
                }
            }

            let r_mean = sum_r / pixels_per_cell;
            let g_mean = sum_g / pixels_per_cell;
            let b_mean = sum_b / pixels_per_cell;
            let r_std = ((sum_r2 / pixels_per_cell) - r_mean * r_mean)
                .max(0.0)
                .sqrt();
            let g_std = ((sum_g2 / pixels_per_cell) - g_mean * g_mean)
                .max(0.0)
                .sqrt();
            let b_std = ((sum_b2 / pixels_per_cell) - b_mean * b_mean)
                .max(0.0)
                .sqrt();
            let luma_mean = sum_l / pixels_per_cell;
            let luma_std = ((sum_l2 / pixels_per_cell) - luma_mean * luma_mean)
                .max(0.0)
                .sqrt();
            let sat_mean = sum_sat / pixels_per_cell;
            let value_mean = sum_v / pixels_per_cell;
            let cell_index = gy * grid_w + gx;
            let delta_luma = if *have_previous {
                (luma_mean - previous_luma[cell_index]).abs()
            } else {
                0.0
            };
            previous_luma[cell_index] = luma_mean;
            screen_energy += delta_luma + luma_std * 0.05;

            output.extend_from_slice(&[
                r_mean, g_mean, b_mean, r_std, g_std, b_std, 0.0, sat_mean, value_mean, luma_mean,
                luma_std, sat_mean, delta_luma, 0.0, luma_std, delta_luma,
            ]);
        }
    }
    *have_previous = true;
    screen_energy
}

struct ChunkMeta {
    path: PathBuf,
    chunk_id: usize,
    frames: usize,
}

fn flush_chunk(
    args: &Args,
    cell_dir: &PathBuf,
    chunks: &mut Vec<ChunkMeta>,
    chunk_frames: &mut Vec<f32>,
    chunk_numbers: &mut Vec<u32>,
) -> Result<(), String> {
    if chunk_numbers.is_empty() {
        return Ok(());
    }
    let chunk_id = chunks.len();
    let path = cell_dir.join(format!("{}_cells_{:04}.tvcells", args.run_id, chunk_id));
    let mut file =
        BufWriter::new(File::create(&path).map_err(|e| format!("chunk open failed: {e}"))?);
    file.write_all(b"TVCELL01")
        .map_err(|e| format!("chunk write failed: {e}"))?;
    for value in [
        chunk_numbers.len() as u32,
        args.grid.1 as u32,
        args.grid.0 as u32,
        FEATURE_NAMES.len() as u32,
    ] {
        file.write_all(&value.to_le_bytes())
            .map_err(|e| format!("chunk write failed: {e}"))?;
    }
    for number in chunk_numbers.iter() {
        file.write_all(&number.to_le_bytes())
            .map_err(|e| format!("chunk write failed: {e}"))?;
    }
    for value in chunk_frames.iter() {
        file.write_all(&value.to_le_bytes())
            .map_err(|e| format!("chunk write failed: {e}"))?;
    }
    file.flush()
        .map_err(|e| format!("chunk flush failed: {e}"))?;
    chunks.push(ChunkMeta {
        path,
        chunk_id,
        frames: chunk_numbers.len(),
    });
    chunk_frames.clear();
    chunk_numbers.clear();
    Ok(())
}

fn write_summary(
    args: &Args,
    run_dir: &PathBuf,
    frame_count: u32,
    duration_seconds: f64,
    source_region: (i32, i32, i32, i32),
) -> Result<(), String> {
    let path = run_dir.join(format!("{}_summary.json", args.run_id));
    let text = format!(
        "{{\n  \"schema_version\": 1,\n  \"kind\": \"truevision_native_rs_summary\",\n  \"run_id\": \"{}\",\n  \"frame_count\": {},\n  \"duration_seconds\": {:.6},\n  \"geometry\": {{\n    \"source_shape\": [{}, {}],\n    \"frame_shape\": [{}, {}],\n    \"grid_shape\": [{}, {}],\n    \"capture_region\": [{}, {}, {}, {}]\n  }}\n}}\n",
        json_escape(&args.run_id),
        frame_count,
        duration_seconds,
        source_region.3,
        source_region.2,
        args.resolution.1,
        args.resolution.0,
        args.grid.1,
        args.grid.0,
        source_region.0,
        source_region.1,
        source_region.2,
        source_region.3,
    );
    std::fs::write(path, text).map_err(|e| format!("summary write failed: {e}"))
}

fn write_manifest(
    args: &Args,
    run_dir: &PathBuf,
    records_path: &PathBuf,
    chunks: &[ChunkMeta],
    frame_count: u32,
    duration_seconds: f64,
    source_region: (i32, i32, i32, i32),
) -> Result<(), String> {
    let path = run_dir.join(format!("{}_manifest.json", args.run_id));
    let mut chunk_lines = Vec::new();
    for chunk in chunks {
        chunk_lines.push(format!(
            "      {{\"chunk_id\": {}, \"path\": \"{}\", \"format\": \"tvcells_f32le_v1\", \"frames\": {}, \"grid_shape\": [{}, {}], \"feature_count\": {}}}",
            chunk.chunk_id,
            json_escape(&chunk.path.display().to_string()),
            chunk.frames,
            args.grid.1,
            args.grid.0,
            FEATURE_NAMES.len()
        ));
    }
    let feature_json = FEATURE_NAMES
        .iter()
        .map(|name| format!("\"{}\"", name))
        .collect::<Vec<_>>()
        .join(", ");
    let text = format!(
        "{{\n  \"schema_version\": 1,\n  \"record_kind\": \"truevision_native_rs_frame_state\",\n  \"run_id\": \"{}\",\n  \"created_at_utc\": \"{}\",\n  \"records_jsonl\": \"{}\",\n  \"config\": {{\n    \"duration_seconds\": {},\n    \"capture_fps\": {},\n    \"capture_resolution\": [{}, {}],\n    \"grid_size_xy\": [{}, {}],\n    \"capture_region\": [{}, {}, {}, {}],\n    \"cell_chunk_frames\": {}\n  }},\n  \"summary\": {{\"frame_count\": {}, \"duration_seconds\": {:.6}}},\n  \"cell_state\": {{\n    \"enabled\": true,\n    \"format\": \"tvcells_f32le_v1\",\n    \"feature_names\": [{}],\n    \"chunks\": [\n{}\n    ]\n  }},\n  \"boundary\": {{\n    \"raw_frame_saved\": false,\n    \"generated_media_is_evidence\": false,\n    \"notes\": \"Native Rust capture writes TrueVision cell state, not raw frames.\"\n  }}\n}}\n",
        json_escape(&args.run_id),
        utc_timestamp(),
        json_escape(&records_path.display().to_string()),
        args.duration,
        args.fps,
        args.resolution.0,
        args.resolution.1,
        args.grid.0,
        args.grid.1,
        source_region.0,
        source_region.1,
        source_region.2,
        source_region.3,
        args.chunk_frames,
        frame_count,
        duration_seconds,
        feature_json,
        chunk_lines.join(",\n"),
    );
    std::fs::write(path, text).map_err(|e| format!("manifest write failed: {e}"))
}

fn source_region(args: &Args, stream: &Stream) -> (i32, i32, i32, i32) {
    if let Some(region) = args.region {
        return region;
    }
    let (width, height) = stream.size().unwrap_or((args.resolution.0 as i32, args.resolution.1 as i32));
    (0, 0, width, height)
}

fn parse_args() -> Result<Args, String> {
    let mut args = env::args().skip(1);
    let mut out = Args {
        duration: 60.0,
        fps: 9.0,
        resolution: (960, 540),
        grid: (160, 90),
        region: None,
        output_root: PathBuf::from("storage/capture_units/incoming"),
        run_id: format!("truevision_rs_{}", timestamp_slug()),
        start_delay: 0.0,
        chunk_frames: 30,
    };
    while let Some(flag) = args.next() {
        let value = match flag.as_str() {
            "--duration"
            | "--fps"
            | "--resolution"
            | "--grid"
            | "--region"
            | "--output-root"
            | "--run-id"
            | "--start-delay"
            | "--cell-chunk-frames" => args
                .next()
                .ok_or_else(|| format!("{flag} requires a value"))?,
            "--help" | "-h" => {
                print_help();
                std::process::exit(0);
            }
            _ => return Err(format!("unknown argument: {flag}")),
        };
        match flag.as_str() {
            "--duration" => out.duration = parse_f64(&value, "duration")?,
            "--fps" => out.fps = parse_f64(&value, "fps")?,
            "--resolution" => out.resolution = parse_pair(&value, "resolution")?,
            "--grid" => out.grid = parse_pair(&value, "grid")?,
            "--region" => out.region = Some(parse_region(&value)?),
            "--output-root" => out.output_root = PathBuf::from(value),
            "--run-id" => out.run_id = value,
            "--start-delay" => out.start_delay = parse_f64(&value, "start-delay")?,
            "--cell-chunk-frames" => {
                out.chunk_frames = value
                    .parse::<usize>()
                    .map_err(|_| "bad cell-chunk-frames".to_string())?
            }
            _ => {}
        }
    }
    Ok(out)
}

fn print_help() {
    println!(
        "truevision_capture_rs --duration 5 --fps 9 --resolution 2560x1440 --grid 640x360 --output-root <dir> --run-id <id>"
    );
}

fn parse_f64(value: &str, name: &str) -> Result<f64, String> {
    value
        .parse::<f64>()
        .map_err(|_| format!("bad {name}: {value}"))
}

fn parse_pair(value: &str, name: &str) -> Result<(usize, usize), String> {
    let parts = value.split('x').collect::<Vec<_>>();
    if parts.len() != 2 {
        return Err(format!("{name} must look like WIDTHxHEIGHT"));
    }
    let width = parts[0]
        .parse::<usize>()
        .map_err(|_| format!("bad {name} width"))?;
    let height = parts[1]
        .parse::<usize>()
        .map_err(|_| format!("bad {name} height"))?;
    if width == 0 || height == 0 {
        return Err(format!("{name} values must be positive"));
    }
    Ok((width, height))
}

fn parse_region(value: &str) -> Result<(i32, i32, i32, i32), String> {
    let parts = value.split(',').collect::<Vec<_>>();
    if parts.len() != 4 {
        return Err("region must look like left,top,width,height".to_string());
    }
    let left = parts[0]
        .parse::<i32>()
        .map_err(|_| "bad region left".to_string())?;
    let top = parts[1]
        .parse::<i32>()
        .map_err(|_| "bad region top".to_string())?;
    let width = parts[2]
        .parse::<i32>()
        .map_err(|_| "bad region width".to_string())?;
    let height = parts[3]
        .parse::<i32>()
        .map_err(|_| "bad region height".to_string())?;
    if width <= 0 || height <= 0 {
        return Err("region width/height must be positive".to_string());
    }
    Ok((left, top, width, height))
}

fn json_escape(value: &str) -> String {
    value.replace('\\', "\\\\").replace('"', "\\\"")
}

fn timestamp_slug() -> String {
    time::OffsetDateTime::now_utc()
        .format(&time::macros::format_description!("[year][month][day]T[hour][minute][second]Z"))
        .expect("static UTC run-id format must be valid")
}

fn utc_timestamp() -> String {
    time::OffsetDateTime::now_utc()
        .format(&time::macros::format_description!(
            "[year]-[month]-[day]T[hour]:[minute]:[second].[subsecond digits:6]Z"
        ))
        .expect("static canonical UTC format must be valid")
}
