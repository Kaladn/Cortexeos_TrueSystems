from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    ok: bool = False
    message: str = ""
    error: Optional[Dict[str, Any]] = None


class StatusResponse(BaseResponse):
    plugin_id: str = "system_pulse"
    version: str = "0.1.0"
    rocm_available: bool = False


class CpuInfo(BaseModel):
    pct: float = 0.0
    cores_logical: int = 0
    cores_physical: int = 0
    freq_mhz: Optional[float] = None
    freq_max_mhz: Optional[float] = None


class MemInfo(BaseModel):
    total_gb: float = 0.0
    used_gb: float = 0.0
    available_gb: float = 0.0
    pct: float = 0.0


class DiskInfo(BaseModel):
    mountpoint: str = ""
    device: str = ""
    fstype: str = ""
    total_gb: float = 0.0
    used_gb: float = 0.0
    free_gb: float = 0.0
    pct: float = 0.0


class GpuDevice(BaseModel):
    id: str = ""
    driver: str = ""
    pct: float = 0.0
    vram_total_gb: Optional[float] = None
    vram_used_gb: Optional[float] = None
    vram_pct: Optional[float] = None


class GpuInfo(BaseModel):
    driver: Optional[str] = None
    gpus: List[GpuDevice] = Field(default_factory=list)
    error: Optional[str] = None


class SnapshotResponse(BaseResponse):
    ts: float = 0.0
    cpu: CpuInfo = Field(default_factory=CpuInfo)
    ram: MemInfo = Field(default_factory=MemInfo)
    swap: MemInfo = Field(default_factory=MemInfo)
    disks: List[DiskInfo] = Field(default_factory=list)
    gpu: GpuInfo = Field(default_factory=GpuInfo)


class HistoryPoint(BaseModel):
    ts: float = 0.0
    cpu_pct: float = 0.0
    ram_pct: float = 0.0


class HistoryResponse(BaseResponse):
    points: List[HistoryPoint] = Field(default_factory=list)
