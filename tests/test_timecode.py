from fractions import Fraction
import pytest
from app.media.timecode import format_timecode, parse_timecode, timestamp_to_frame, relative_frame_to_tc, tc_to_relative_frame


def test_25fps_frame_labels_and_unbounded_hours():
    assert format_timecode(25 * 3600 + 26) == "01:00:01:01"
    assert parse_timecode("01:00:01:01") == 90026
    assert format_timecode(25 * 86400) == "24:00:00:00"
    assert parse_timecode("24:00:00:00") == 25 * 86400
    assert timestamp_to_frame(Fraction(1, 25)) == 1
    assert timestamp_to_frame("0.039999") == 0


@pytest.mark.parametrize("frame,tc", [(0,"00:00:00;00"),(1799,"00:00:59;29"),(1800,"00:01:00;02"),(17981,"00:09:59;29"),(17982,"00:10:00;00"),(107892,"01:00:00;00"),(2589408,"24:00:00;00")])
def test_2997_drop_boundaries(frame, tc):
    assert format_timecode(frame, 30000, 1001, True) == tc
    assert parse_timecode(tc, 30000, 1001, True) == frame


@pytest.mark.parametrize("rate,drop", [((25,1),False),((24000,1001),False),((30000,1001),False),((30000,1001),True),((60000,1001),True)])
def test_roundtrip(rate, drop):
    for frame in [0,1,24,25,59,1799,1800,3599,3600,17981,17982,35964,107891,107892,9876543]:
        assert parse_timecode(format_timecode(frame,*rate,drop),*rate,drop) == frame


def test_5994_drop_boundary():
    assert format_timecode(3599,60000,1001,True) == "00:00:59;59"
    assert format_timecode(3600,60000,1001,True) == "00:01:00;04"
    assert timestamp_to_frame("1.001",30000,1001) == 30


@pytest.mark.parametrize("tc", ["00:01:00;00","00:01:00;01","00:59:00;01"])
def test_reject_impossible_df_labels(tc):
    with pytest.raises(ValueError): parse_timecode(tc,30000,1001,True)


@pytest.mark.parametrize("tc", ["00:60:00:00","00:00:60:00","00:00:00:25","00:00:00;00","wrong","-1:00:00:00"])
def test_reject_bad_labels(tc):
    with pytest.raises(ValueError): parse_timecode(tc)


def test_manual_origin_roundtrip():
    media={"fps_numerator":30000,"fps_denominator":1001,"drop_frame":True,"start_timecode":"01:00:00;00"}
    assert relative_frame_to_tc(media,1800) == "01:01:00;02"
    assert tc_to_relative_frame(media,"01:01:00:02") == 1800
    with pytest.raises(ValueError): tc_to_relative_frame(media,"00:59:59;29")
    with pytest.raises(ValueError): format_timecode(1,25,1,True)
