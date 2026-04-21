from __future__ import annotations


def format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{size} B"


MODEL_DOWNLOAD_METADATA = {
    "marker": {
        "engine": "marker",
        "models": [
            {
                "name": "layout",
                "download_url": "https://models.datalab.to/layout/2025_09_23/manifest.json",
                "model_size": format_bytes(1445594819),
            },
            {
                "name": "text_recognition",
                "download_url": "https://models.datalab.to/text_recognition/2025_09_23/manifest.json",
                "model_size": format_bytes(1439035487),
            },
            {
                "name": "ocr_error_detection",
                "download_url": "https://models.datalab.to/ocr_error_detection/2025_02_18/manifest.json",
                "model_size": format_bytes(274584088),
            },
            {
                "name": "table_recognition",
                "download_url": "https://models.datalab.to/table_recognition/2025_02_18/manifest.json",
                "model_size": format_bytes(211235404),
            },
            {
                "name": "text_detection",
                "download_url": "https://models.datalab.to/text_detection/2025_05_07/manifest.json",
                "model_size": format_bytes(76939626),
            },
        ],
    },
    "mineru": {
        "engine": "mineru",
        "models": [
            {
                "name": "PDF-Extract-Kit-1.0",
                "download_url": "https://huggingface.co/opendatalab/PDF-Extract-Kit-1.0",
                "model_size": format_bytes(2494489380),
            },
            {
                "name": "MinerU2.5-Pro-2604-1.2B",
                "download_url": "https://huggingface.co/opendatalab/MinerU2.5-Pro-2604-1.2B",
                "model_size": format_bytes(2328026289),
            },
        ],
    },
}


def get_download_metadata(engine: str) -> dict:
    metadata = MODEL_DOWNLOAD_METADATA.get(engine, {"engine": engine, "models": []})
    return {
        "engine": metadata["engine"],
        "models": [dict(model) for model in metadata.get("models", [])],
    }
