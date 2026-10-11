from clipper.captions import _ts, build_ass, group_words
from clipper.highlights import ClipIdea, finalize, snap_to_words, transcript_lines
from clipper.models import Word
from clipper.reframe import Face, VideoInfo, plan_crop, x_expression

INFO = VideoInfo(1920, 1080, 30.0, 600.0)


def words_from(text: str, start: float = 0.0, step: float = 0.4) -> list[Word]:
    out, t = [], start
    for w in text.split():
        out.append(Word(round(t, 3), round(t + step * 0.8, 3), w))
        t += step
    return out


def test_transcript_lines_break_on_sentences():
    lines = transcript_lines(words_from("Hola a todos. ¿Cómo están? Bien"))
    assert [t for _, _, t in lines] == ["Hola a todos.", "¿Cómo están?", "Bien"]


def test_snap_to_words_aligns_and_pads():
    words = words_from(" ".join(["palabra"] * 200))
    s, e = snap_to_words(10.1, 40.0, words, min_seconds=20, max_seconds=60)
    assert s == round(10.0 - 0.15, 3)  # nearest word start to 10.1 is 10.0
    assert e <= 40.0 + 0.5 + 0.15


def test_snap_to_words_enforces_max_length():
    words = words_from(" ".join(["palabra"] * 300))
    s, e = snap_to_words(0, 100, words, min_seconds=20, max_seconds=60)
    assert e - s <= 60


def test_snap_rejects_too_short():
    words = words_from("uno dos tres")
    assert snap_to_words(0, 1.2, words, min_seconds=20, max_seconds=60) is None


def test_finalize_drops_overlaps_and_sorts():
    words = words_from(" ".join(["palabra"] * 400))
    idea = lambda s, e, score: ClipIdea(start=s, end=e, title="t", hook="h", description="d",
                                        hashtags=["#Tag Uno"], score=score, reason="r")
    clips = finalize([idea(100, 130, 6), idea(10, 40, 9), idea(20, 50, 8)], words, 20, 60, 5)
    assert [round(c.start) for c in clips] == [10, 100]
    assert clips[0].hashtags == ["TagUno"]


def face_samples(xs_by_time):
    return [(t, [Face(x, 540, 200, 200) for x in xs]) for t, xs in xs_by_time]


def test_plan_crop_jumps_on_camera_cut():
    samples = face_samples([(i / 3, [400] if i < 30 else [1500]) for i in range(60)])
    plan = plan_crop(samples, INFO)
    assert plan.mode == "crop"
    assert len(plan.keyframes) == 2
    assert plan.keyframes[1][0] == 10.0
    assert plan.keyframes[0][1] < plan.keyframes[1][1]


def test_plan_crop_ignores_small_jitter():
    samples = face_samples([(i / 3, [900 + (i % 3) * 20]) for i in range(30)])
    assert len(plan_crop(samples, INFO).keyframes) == 1


def test_plan_crop_fit_for_wide_two_shot():
    samples = face_samples([(i / 3, [300, 1600]) for i in range(30)])
    assert plan_crop(samples, INFO).mode == "fit"


def test_plan_crop_without_faces_centers():
    plan = plan_crop([(i / 3, []) for i in range(10)], INFO)
    assert plan.keyframes == [(0.0, (1920 - plan.crop_w) // 2)]


def test_x_expression():
    assert x_expression([(0.0, 10)]) == "10"
    assert x_expression([(0.0, 10), (5.0, 20), (9.0, 30)]) == "if(lt(t,5.0),10,if(lt(t,9.0),20,30))"


def test_ass_timestamps_and_events():
    assert _ts(3725.456) == "1:02:05.46"
    words = words_from("hola qué tal, esto es una prueba", start=100)
    ass = build_ass(words, 99.5, 104.0, hook="El gancho")
    assert "Style: Cap" in ass and "Hook,,0,0,0,,EL GANCHO" in ass
    assert ass.count("Dialogue: 0,") == len(words)
    assert "0:00:00.50" in ass  # first word shifted to clip time
    assert "TAL," not in ass  # trailing punctuation stripped


def test_group_words_breaks_on_punctuation():
    groups = group_words(words_from("hola qué tal, esto es"))
    assert [len(g) for g in groups] == [3, 2]
