#!/usr/bin/env bash
# Bench abort test for the wiring-B bridge: webcam + `bridge run`, an
# optional kill -9 of the bridge mid-run, then `forward` so the keypad
# works again. Usage: [START_VAC=N] abort_test.sh LABEL RPM ACCEL HOLD
# MIN_VAC [KILL_S]
set -u
cd "$(dirname "$0")/../.."
label=$1 rpm=$2 accel=$3 hold=$4 min_vac=$5 kill_after=${6:-}
D=claude_test/rs232_probe/sessions/$(date +%Y%m%d_%H%M%S)_$label
mkdir -p "$D"
echo "$D"
K=/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_BHCWb144J08-if00-port0
M=/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_AUCGb144J08-if00-port0
B="python3 -u -m spincoater_midas.bridge --keypad-port $K --mainboard-port $M"
ffmpeg -hide_banner -loglevel error -f v4l2 -input_format mjpeg \
    -video_size 1280x720 -framerate 15 -i /dev/video0 -t 150 \
    -vf "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='%{localtime\:%H\\\\\:%M\\\\\:%S}':x=20:y=20:fontsize=40:fontcolor=white:box=1:boxcolor=black@0.6" \
    -c:v libx264 -preset veryfast -crf 26 -y "$D/video.mp4" \
    > "$D/ffmpeg.log" 2>&1 &
camera=$!
date +%T.%N | cut -c1-12
$B --log "$D/run.csv" run --rpm "$rpm" --accel "$accel" --hold "$hold" \
    --min-vacuum "$min_vac" ${START_VAC:+--start-vacuum "$START_VAC"} --yes \
    > "$D/run.out" 2>&1 &
bridge=$!
if [ -n "$kill_after" ]; then
    until grep -q run_start "$D/run.csv" 2>/dev/null; do
        kill -0 $bridge 2>/dev/null || break
        sleep 0.05
    done
    sleep "$kill_after"
    kill -9 $bridge && echo "killed bridge at $(date +%T.%N | cut -c1-12)"
    sleep 5
fi
wait $bridge 2>/dev/null
uniq "$D/run.out"
echo "forward from $(date +%T.%N | cut -c1-12)"
$B --log "$D/forward.csv" forward --seconds 30
date +%T.%N | cut -c1-12
kill -INT $camera 2>/dev/null
wait $camera 2>/dev/null
exit 0
