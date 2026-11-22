from lib.discovery.normalize import DiscoveryHit
from lib.discovery.profile import OssProfile, OssSignalKeywords
from lib.discovery.ranker import rank_oss_resource


def _profile() -> OssProfile:
    return OssProfile(
        signals=OssSignalKeywords(
            task_keywords=["speech recognition", "ASR", "translation"],
            language_keywords=["low-resource", "multilingual"],
            target_language_codes=["ht"],
            target_language_names=["haitian creole"],
            license_preferred=["mit", "apache-2.0"],
        )
    )


def test_target_language_dataset_ranks_above_generic_repo():
    target = DiscoveryHit(
        name="haitian-creole-asr",
        url="https://huggingface.co/datasets/x/ht-asr",
        resource_type="dataset",
        source="huggingface",
        description="Speech recognition corpus for Haitian Creole (ht), low-resource ASR",
        license="apache-2.0",
        stars=40,
        language_tags=["ht"],
    )
    generic = DiscoveryHit(
        name="todo-app",
        url="https://github.com/x/todo",
        resource_type="repo",
        source="github",
        description="A todo list in React",
        license="gpl-3.0",
        stars=5,
    )
    profile = _profile()
    ranked_target = rank_oss_resource(target, profile)
    ranked_generic = rank_oss_resource(generic, profile)

    assert ranked_target.target_language_match is True
    assert ranked_generic.target_language_match is False
    assert ranked_target.scores.total > ranked_generic.scores.total
    assert "Haitian Creole match" in ranked_target.rank_reason


def test_language_code_requires_word_boundary():
    # "ht" must not match inside "right" or "https".
    hit = DiscoveryHit(
        name="rightsizing",
        url="https://example.com",
        resource_type="repo",
        source="github",
        description="Get the right size, see https docs",
    )
    assert rank_oss_resource(hit, _profile()).target_language_match is False
