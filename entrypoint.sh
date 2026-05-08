#!/bin/sh
Xvfb :99 -screen 0 1024x768x24 -nolisten tcp &
export DISPLAY=:99
exec uvicorn image_converter.web:app --host 0.0.0.0 --port 8000
