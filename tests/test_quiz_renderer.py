"""Tests for quiz renderer."""

import numpy as np
import pytest
from PIL import Image

from brainrot.config import VideoConfig
from brainrot.quiz_config import TriviaQuestion, WYRQuestion
from brainrot.quiz_renderer import (
    load_character_image,
    render_countdown_bar,
    render_question_frame,
    render_trivia_frame,
    render_wyr_frame,
)


@pytest.fixture
def small_video():
    return VideoConfig(width=540, height=960, fps=30)


@pytest.fixture
def trivia_q():
    return TriviaQuestion(
        question="What is the capital of France?",
        options=("Berlin", "Paris", "London", "Madrid"),
        correct=1,
        time_limit=7.0,
    )


@pytest.fixture
def wyr_q():
    return WYRQuestion(
        option_a="Have unlimited money",
        option_b="Have unlimited time",
        time_limit=6.0,
    )


class TestTriviaFrame:
    def test_output_size(self, trivia_q, small_video):
        img = render_trivia_frame(trivia_q, small_video)
        assert img.size == (540, 960)
        assert img.mode == "RGBA"

    def test_has_content(self, trivia_q, small_video):
        img = render_trivia_frame(trivia_q, small_video)
        arr = np.array(img)
        assert arr[:, :, 3].sum() > 0

    def test_reveal_has_green_pixels(self, trivia_q, small_video):
        img = render_trivia_frame(trivia_q, small_video, reveal=True)
        arr = np.array(img)
        green_dominant = arr[:, :, 1] > arr[:, :, 0]
        assert green_dominant.sum() > 0

    def test_no_reveal_fewer_green_pixels(self, trivia_q, small_video):
        reveal_img = render_trivia_frame(trivia_q, small_video, reveal=True)
        no_reveal_img = render_trivia_frame(trivia_q, small_video, reveal=False)
        reveal_arr = np.array(reveal_img)
        no_reveal_arr = np.array(no_reveal_img)
        green_mask_reveal = (reveal_arr[:, :, 1] > 150) & (reveal_arr[:, :, 1] > reveal_arr[:, :, 0] + 50)
        green_mask_no = (no_reveal_arr[:, :, 1] > 150) & (no_reveal_arr[:, :, 1] > no_reveal_arr[:, :, 0] + 50)
        assert green_mask_reveal.sum() > green_mask_no.sum()

    def test_with_question_index(self, trivia_q, small_video):
        img = render_trivia_frame(
            trivia_q, small_video, question_index=2, total_questions=5
        )
        assert img.size == (540, 960)
        arr = np.array(img)
        assert arr[:, :, 3].sum() > 0

    def test_reveal_dims_wrong_answers(self, trivia_q, small_video):
        reveal_img = render_trivia_frame(trivia_q, small_video, reveal=True)
        no_reveal_img = render_trivia_frame(trivia_q, small_video, reveal=False)
        reveal_arr = np.array(reveal_img)
        no_reveal_arr = np.array(no_reveal_img)
        # reveal frame should differ from non-reveal (dimming + glow)
        assert not np.array_equal(reveal_arr, no_reveal_arr)


class TestWYRFrame:
    def test_output_size(self, wyr_q, small_video):
        img = render_wyr_frame(wyr_q, small_video)
        assert img.size == (540, 960)
        assert img.mode == "RGBA"

    def test_has_content(self, wyr_q, small_video):
        img = render_wyr_frame(wyr_q, small_video)
        arr = np.array(img)
        assert arr[:, :, 3].sum() > 0

    def test_with_question_index(self, wyr_q, small_video):
        img = render_wyr_frame(wyr_q, small_video, question_index=1, total_questions=3)
        assert img.size == (540, 960)


class TestCountdownBar:
    def test_full_bar(self, small_video):
        img = render_countdown_bar(small_video, progress=0.0)
        assert img.size == (540, 960)
        assert img.mode == "RGBA"

    def test_empty_bar(self, small_video):
        img = render_countdown_bar(small_video, progress=1.0)
        assert img.size == (540, 960)

    def test_half_bar(self, small_video):
        img = render_countdown_bar(small_video, progress=0.5)
        arr = np.array(img)
        assert arr[:, :, 3].sum() > 0

    def test_low_time_changes_color(self, small_video):
        normal_img = render_countdown_bar(small_video, progress=0.3)
        low_img = render_countdown_bar(small_video, progress=0.85)
        normal_arr = np.array(normal_img)
        low_arr = np.array(low_img)
        # low time bar should have more red pixels
        red_normal = (normal_arr[:, :, 0] > 200).sum()
        red_low = (low_arr[:, :, 0] > 200).sum()
        assert red_low > red_normal


class TestCharacterImage:
    def test_file_not_found(self, tmp_path, small_video):
        with pytest.raises(FileNotFoundError):
            load_character_image(tmp_path / "missing.png", small_video)

    def test_load_and_scale(self, tmp_path, small_video):
        char = Image.new("RGBA", (200, 300), (255, 0, 0, 255))
        path = tmp_path / "char.png"
        char.save(path)

        result = load_character_image(path, small_video, target_width_frac=0.20)
        expected_w = int(540 * 0.20)
        assert result.width == expected_w
        assert result.mode == "RGBA"
        expected_h = int(expected_w * (300 / 200))
        assert result.height == expected_h


class TestRenderQuestionFrame:
    def test_dispatches_trivia(self, trivia_q, small_video):
        img = render_question_frame(trivia_q, small_video)
        assert img.size == (540, 960)

    def test_dispatches_wyr(self, wyr_q, small_video):
        img = render_question_frame(wyr_q, small_video)
        assert img.size == (540, 960)

    def test_trivia_reveal(self, trivia_q, small_video):
        img = render_question_frame(trivia_q, small_video, reveal=True)
        assert img.size == (540, 960)

    def test_passes_question_index(self, trivia_q, small_video):
        img = render_question_frame(
            trivia_q, small_video, question_index=3, total_questions=10
        )
        assert img.size == (540, 960)
