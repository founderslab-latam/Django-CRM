"""
Unit tests for the Chilean RUT validator.

Run with: pytest common/tests/test_rut_validator.py -v
"""

import pytest
from django.core.exceptions import ValidationError

from common.validators import (
    format_rut,
    normalize_rut,
    rut_check_digit,
    validate_rut,
)


class TestNormalizeRut:
    def test_strips_dots_and_dash(self):
        assert normalize_rut("12.345.678-5") == "123456785"

    def test_upper_cases_k(self):
        assert normalize_rut("12.345.670-k") == "12345670K"

    def test_trims_surrounding_space(self):
        assert normalize_rut("  12345678-5  ") == "123456785"

    @pytest.mark.parametrize("blank", ["", None])
    def test_blank_stays_blank(self, blank):
        assert normalize_rut(blank) == ""


class TestRutCheckDigit:
    @pytest.mark.parametrize(
        "body,dv",
        [
            ("12345678", "5"),
            ("11111111", "1"),
            ("1234567", "4"),
            ("12345670", "K"),  # remainder 10
            ("12345675", "0"),  # remainder 11
        ],
    )
    def test_known_digits(self, body, dv):
        assert rut_check_digit(body) == dv


class TestValidateRut:
    @pytest.mark.parametrize(
        "raw",
        [
            "12.345.678-5",
            "12345678-5",
            "123456785",
            " 12.345.678-5 ",
        ],
    )
    def test_accepts_every_accepted_shape(self, raw):
        assert validate_rut(raw) == "12.345.678-5"

    def test_accepts_and_canonicalises_k(self):
        assert validate_rut("12345670k") == "12.345.670-K"

    def test_accepts_seven_digit_body(self):
        assert validate_rut("1234567-4") == "1.234.567-4"

    def test_rejects_wrong_check_digit(self):
        with pytest.raises(ValidationError):
            validate_rut("12.345.678-9")

    @pytest.mark.parametrize(
        "garbage",
        [
            "not-a-rut",
            "123",  # body too short
            "1234567890123-5",  # body too long
            "12.345.678-Z",  # check digit neither digit nor K
            "",  # blank is not a valid RUT (callers guard blank themselves)
        ],
    )
    def test_rejects_garbage(self, garbage):
        with pytest.raises(ValidationError):
            validate_rut(garbage)


class TestFormatRut:
    def test_groups_a_bare_rut(self):
        assert format_rut("123456785") == "12.345.678-5"

    def test_is_idempotent_on_canonical_form(self):
        assert format_rut("12.345.678-5") == "12.345.678-5"
