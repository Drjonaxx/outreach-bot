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


def test_load_audio_decodes_16k_mono(tmp_path):
    import subprocess
    from clipper.transcribe import SAMPLE_RATE, load_audio
    wav = tmp_path / "tone.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                    "-ac", "2", "-ar", "44100", str(wav)], check=True)
    audio = load_audio(str(wav))
    assert audio.dtype.name == "float32"
    assert abs(len(audio) - 2 * SAMPLE_RATE) < 200
    assert 0.1 < abs(audio).max() <= 1.0


def test_keep_ranges_jump_cuts_long_silences():
    from clipper.models import Clip
    from clipper.render import keep_ranges, remap
    words = [Word(0.0, 0.5, "a"), Word(0.6, 1.0, "b"), Word(6.0, 6.5, "c"), Word(6.6, 7.0, "d")]
    clip = Clip(0.0, 7.2, "t", "h", "d", [], 5, "r")
    ranges = keep_ranges(clip, words, max_gap=3.0, pad=0.5)
    assert ranges == [(0.0, 1.5), (5.5, 7.2)]
    assert remap(6.0, ranges) == 2.0
    assert keep_ranges(clip, words, max_gap=0) == [(0.0, 7.2)]


def test_keep_ranges_respects_explicit_pieces():
    from clipper.models import Clip
    from clipper.render import keep_ranges
    words = [Word(0.0, 0.5, "a"), Word(3.0, 3.5, "slur"), Word(6.0, 6.5, "c")]
    clip = Clip(0.0, 7.0, "t", "h", "d", [], 5, "r", keep=[[0.0, 1.0], [5.8, 7.0]])
    assert keep_ranges(clip, words, max_gap=3.0) == [(0.0, 1.0), (5.8, 7.0)]


def test_censor_only_swears():
    from clipper.captions import _clean
    assert [_clean(w) for w in ["fucking", "shit?", "bitch", "bit", "fun", "shift"]] == \
        ["F*CKING", "SH*T?", "B*TCH", "BIT", "FUN", "SHIFT"]


def test_phrase_subs_ass_labels_and_wraps():
    from clipper.captions import build_subs_ass
    ass = build_subs_ass([{"start": 0.5, "end": 2.0, "text": "CHAT: Espero que hayas traído tu flotador."},
                          {"start": 9.0, "end": 12.0, "text": "fuera del clip"}], duration=5.0,
                         hook="¿Lo dijo mal a propósito?")
    events = ass.split("[Events]")[1]
    assert "¿LO DIJO MAL A" in events
    assert "CHAT:{\\c&H00FFFFFF&} Espero" in events and "\\N" in events
    assert "fuera del clip" not in events


def test_render_keeps_sync_across_audio_dropouts(tmp_path):
    """A VOD with an audio gap must not pull later audio forward after cutting."""
    import subprocess
    from clipper.models import Clip
    from clipper.reframe import probe
    from clipper.render import render_clip
    src = tmp_path / "gap.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30:duration=12",
                    "-f", "lavfi", "-i", "sine=frequency=800:duration=12",
                    "-filter_complex", "[1:a]aselect='not(between(t,4,6))'[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-c:a", "aac", str(src)], check=True)
    clip = Clip(2.0, 10.0, "t", "", "", [], 5, "r", keep=[[2.0, 3.5], [5.5, 10.0]])
    out = tmp_path / "out.mp4"
    render_clip(str(src), probe(str(src)), clip, [], out, captions=False, layout="fit", max_gap=0)
    durs = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=duration", "-of", "csv=p=0", str(out)],
                          capture_output=True, text=True, check=True).stdout.split()
    video, audio = (float(x) for x in durs)
    assert abs(video - audio) < 0.15


def _clipkit():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("clipkit", Path(__file__).parents[1] / "tools" / "clipkit.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_posting_queue_fills_slots_and_retries():
    from datetime import datetime
    ck = _clipkit()
    morning = datetime(2026, 10, 13, 10, 30, tzinfo=ck.PR)
    queue = []
    n = ck.PER_SLOT
    for i in range(2 * n + 2):
        item = {"id": f"x/{i:02d}", "results": {}}
        item["at"] = ck.free_slot(queue, morning)
        queue.append(item)
    assert [q["at"] for q in queue] == ["2026-10-13T11:53"] * n + ["2026-10-13T19:56"] * n + ["2026-10-14T11:53"] * 2
    # Rendered after the noon slot: straight to tonight.
    assert ck.free_slot([], datetime(2026, 10, 13, 13, 0, tzinfo=ck.PR)) == "2026-10-13T19:56"

    noon = datetime(2026, 10, 13, 11, 53, tzinfo=ck.PR)
    due = ck.due_items(queue, ["youtube", "instagram"], noon)
    assert [d["id"] for d in due] == [f"x/{i:02d}" for i in range(n)]
    ck.merge_results(queue, {"x/00": {"youtube": {"id": "abc", "url": "u"}, "instagram": {"pending": "c1"}},
                             "x/01": {"youtube": {"error": "boom"}, "instagram": {"id": "m1"}}})
    due = {d["id"]: d for d in ck.due_items(queue, ["youtube", "instagram"], noon)}
    assert due["x/00"]["platforms"] == ["instagram"] and due["x/00"]["pending"] == {"instagram": "c1"}
    assert due["x/01"]["platforms"] == ["youtube"]
    for _ in range(2):
        ck.merge_results(queue, {"x/01": {"youtube": {"error": "boom"}}})
    assert "x/01" not in {d["id"] for d in ck.due_items(queue, ["youtube", "instagram"], noon)}  # gave up
    # Two days later the old clips are dropped.
    assert ck.due_items(queue, ["youtube"], datetime(2026, 10, 16, 12, 0, tzinfo=ck.PR)) == []


def test_post_fields_reuse_caption_and_skip_repeated_hashtags():
    ck = _clipkit()
    meta = {"description": "Se pone raro.", "url": "https://kick.com/x/videos/1",
            "tags": ["gtarp", "quedijoelgringo", "shorts"]}
    item = ck.post_fields("lordkebun-1", 6, "Papi Pistone 😂 🎥LordKebun (Kick) #quedijoelgringo", meta)
    assert item["id"] == "lordkebun-1/06" and item["url"].endswith("/lordkebun-1/clip_06.mp4")
    assert item["title"].startswith("Papi Pistone")
    assert item["description"].endswith("#gtarp #shorts") and "kick.com/x/videos/1" in item["description"]
    assert item["ig_caption"].count("#quedijoelgringo") == 1 and item["tags"] == ["gtarp", "quedijoelgringo"]
    assert "de LordKebun" in item["comment"]


def test_youtube_private_upload_then_release():
    from datetime import datetime
    ck = _clipkit()
    queue = [{"id": "x/01", "at": "2026-10-16T11:53", "results": {}},
             {"id": "x/02", "at": "2026-10-16T19:56", "results": {}}]
    early = datetime(2026, 10, 16, 4, 7, tzinfo=ck.PR)
    assert [d["id"] for d in ck.upcoming_items(queue, early, 20)] == ["x/01", "x/02"]
    assert ck.due_items(queue, ["youtube"], early) == []
    ck.merge_results(queue, {"x/01": {"youtube": {"private_id": "v1"}},
                             "x/02": {"youtube": {"error": "Status: 429 Quota exceeded"}}})
    assert queue[1]["results"]["youtube"]["tries"] == 0  # quota errors don't count
    assert [d["id"] for d in ck.upcoming_items(queue, early, 20)] == ["x/02"]
    due = ck.due_items(queue, ["youtube"], datetime(2026, 10, 16, 11, 53, tzinfo=ck.PR))
    assert due[0]["youtube_private_id"] == "v1"
    ck.merge_results(queue, {"x/01": {"youtube": {"private_id": "v1", "error": "boom"}}})
    assert queue[0]["results"]["youtube"]["tries"] == 0
    ck.merge_results(queue, {"x/01": {"youtube": {"id": "v1", "url": "u"}}})
    assert ck.due_items(queue, ["youtube"], datetime(2026, 10, 16, 12, 0, tzinfo=ck.PR)) == []
