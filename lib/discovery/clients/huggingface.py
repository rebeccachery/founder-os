import os

from huggingface_hub import HfApi

from lib.discovery.normalize import DiscoveryHit


def _get_api() -> HfApi:
    token = os.getenv("HF_TOKEN") or None
    return HfApi(token=token)


def search_hf_models(query: str, max_results: int = 10) -> list[DiscoveryHit]:
    api = _get_api()
    hits: list[DiscoveryHit] = []
    try:
        for model in api.list_models(search=query, limit=max_results, sort="downloads"):
            model_id = model.id or ""
            if not model_id:
                continue
            org = model_id.split("/")[0] if "/" in model_id else None
            tags = list(model.tags or [])
            hits.append(
                DiscoveryHit(
                    name=model_id,
                    url=f"https://huggingface.co/{model_id}",
                    description=getattr(model, "description", None) or "",
                    resource_type="model",
                    source="huggingface",
                    organization=org,
                    license=getattr(model, "license", None),
                    stars=getattr(model, "downloads", None),
                    task_tags=[t for t in tags if not t.startswith("license:")],
                    last_updated_at=model.last_modified.isoformat() if model.last_modified else None,
                    raw={"model_id": model_id, "pipeline_tag": getattr(model, "pipeline_tag", None)},
                )
            )
    except Exception:
        return hits
    return hits


def search_hf_datasets(query: str, max_results: int = 10) -> list[DiscoveryHit]:
    api = _get_api()
    hits: list[DiscoveryHit] = []
    try:
        for dataset in api.list_datasets(search=query, limit=max_results, sort="downloads"):
            dataset_id = dataset.id or ""
            if not dataset_id:
                continue
            org = dataset_id.split("/")[0] if "/" in dataset_id else None
            tags = list(dataset.tags or [])
            hits.append(
                DiscoveryHit(
                    name=dataset_id,
                    url=f"https://huggingface.co/datasets/{dataset_id}",
                    description=getattr(dataset, "description", None) or "",
                    resource_type="dataset",
                    source="huggingface",
                    organization=org,
                    license=getattr(dataset, "license", None),
                    stars=getattr(dataset, "downloads", None),
                    task_tags=tags,
                    last_updated_at=dataset.last_modified.isoformat() if dataset.last_modified else None,
                    raw={"dataset_id": dataset_id},
                )
            )
    except Exception:
        return hits
    return hits
