from __future__ import annotations

from collections import Counter

from awrag.nlp_resolver import best_sentence, resolve_answer


def test_best_sentence_keeps_eg_abbreviation_inside_sentence() -> None:
    text = (
        "3. It is not necessary to excuse a person who has had a particular life "
        "experience (e.g. a victim of a sexual offence) from serving on a jury in "
        "a trial which concerns matters to which that experience is relevant "
        "(e.g. a sexual offence trial). It should not be assumed that such a "
        "person is any more likely to be prejudiced than other jurors."
    )

    sentence = best_sentence(text, Counter({"excuse": 1, "juror": 1, "jury": 1, "offence": 1, "serving": 1}))

    assert "e.g. a victim of a sexual offence" in sentence
    assert "e.g. a sexual offence trial" in sentence
    assert sentence.startswith("It is not necessary to excuse")
    assert not sentence.startswith("a victim of")


def test_resolve_answer_does_not_render_abbreviation_fragment() -> None:
    packet = {
        "locations": [
            {
                "citation": "[AWCIT-eg]",
                "text": (
                    "3. It is not necessary to excuse a person who has had a particular life "
                    "experience (e.g. a victim of a sexual offence) from serving on a jury in "
                    "a trial which concerns matters to which that experience is relevant "
                    "(e.g. a sexual offence trial)."
                ),
            }
        ]
    }

    answer = resolve_answer("juror jury excuse offence serving trial", packet)

    assert answer["status"] == "answered_from_awrag_locations"
    assert "It is not necessary to excuse" in answer["text"]
    assert "e.g. a victim of a sexual offence" in answer["text"]
    assert " [AWCIT-eg]" in answer["text"]


def test_resolve_answer_renders_dataset_backed_greeting_as_crisp_reply() -> None:
    packet = {
        "locations": [
            {"citation": "[AWCIT-morning]", "text": "Morning! All good - given the marathon yesterday, good morning was implied."},
            {"citation": "[AWCIT-good]", "text": "oh! LOL. Good morning I forgot to say it."},
        ]
    }

    answer = resolve_answer("Good morning.", packet)

    assert answer["status"] == "answered_from_awrag_locations"
    assert answer["text"] == "Good morning."
    assert answer["citations"] == ["[AWCIT-morning]", "[AWCIT-good]"]
    assert answer["conversation_reply_receipt"]["input_class"] == "greeting"
    assert answer["conversation_reply_receipt"]["reply_source"] == "admitted_cited_evidence"


def test_best_sentence_keeps_dataset_dotted_abbreviation_class() -> None:
    text = (
        "The trial judge gave the jury a limiting direction, i.e. a direction "
        "about the permitted use of evidence. A comparison point appears c.f. "
        "other directions in W.L.R. reports."
    )

    sentence = best_sentence(text, Counter({"direction": 1, "evidence": 1, "jury": 1}))

    assert "i.e. a direction" in sentence
    assert sentence.startswith("The trial judge")


def test_best_sentence_keeps_cf_and_report_abbreviations() -> None:
    text = (
        "The first sentence is unrelated. A comparison point appears c.f. other "
        "directions in W.L.R. reports."
    )

    sentence = best_sentence(text, Counter({"comparison": 1, "directions": 1, "reports": 1}))

    assert "c.f. other directions" in sentence
    assert "W.L.R. reports" in sentence
    assert sentence.startswith("A comparison point")
