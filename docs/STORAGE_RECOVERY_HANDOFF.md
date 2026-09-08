# Storage recovery pause — 2026-09-08

## SUPERSEDING USER DECISION

User cancelled the NVMe rebuild and identified the secondary drive as Steam.
Do not erase, repartition, or relocate its contents. Keep the original and the
verified Projects recovery copy. The recorder now uses existing free space on
`/run/media/lamercey/New Volume`, creating a fresh TrueVision-Logs folder per run.
The migration gates below are historical, NOT current execution instructions.
Next: qualify live clarity and graceful sealing on the SATA destination, then
return to the unfinished evidence test. Leave training and backup data alone.

Controlling user request: preserve work, recover secondary NVMe into existing
Projects, then provision only that NVMe for TrueVision. Do not touch training
data, the 5TB backup, or the active system disk. Prior backup-drive recording
destination is superseded. No recovery data belongs in Git.

Protected system: WD_BLACK SN770 2TB, serial 24423R800793, currently nvme0n1.
Root is LUKS fac0c571-8742-4026-8d71-eb93453e9d1b -> Btrfs
ea807b99-e497-49fa-9054-d13f67cc7b81; boot UUID 7B44-0809.
Projects is /home/lamercey/Projects on that system Btrfs filesystem.

Target only: SHGP31-2000GM, serial ASCCN48441110CG4F, currently nvme1n1.
Its old home UUID is cedde945-add8-496b-8c11-5f9626103afd.
Recovery destination: /home/lamercey/Projects/Recovered-NVMe-ASCCN48441110CG4F.
Copying the readable deck directory is not clearance to erase: root-owned
offload/root and other rootfs locations still require privileged inspection.

Next gates:
1. Finish copy and independently hash-verify paths, bytes, links and metadata;
   retain manifests under external system/output, never in this repository.
2. Inspect all target partitions for valuable material using administrator
   access; exclude only established obsolete OS content. sudo currently needs
   authentication. Do not infer that inaccessible content is disposable.
3. Recheck serial, system ancestry and separate destination immediately before
   destructive work. Only then recreate target GPT + one ext4 data filesystem.
4. Mount target at /mnt/truevision by new UUID with lamercey-owned recording
   directory. Qualify write/read/hash/delete, mount, partition map and recorder.
5. Inventory non-TrueSystems repos, including dirty/untracked files and external
   path references, before copy/verify/relocate to SATA SSD. Preserve original
   locations until validated; names alone do not classify system membership.
6. Complete the previously unfinished AWRAG evidence test after storage is safe.
   Training data remains untouched; no training repair or spending authorized.

Recording now fails closed if /mnt/truevision is absent. No backup fallback.
The CLI seal has fixture coverage, not live terminal-close qualification.
No reboot was performed: current mount ancestry is evidence of the running
system, not a new boot test. No disk wipe or partition change is authorized by
this document alone; the user's conditional authorization requires all gates.
