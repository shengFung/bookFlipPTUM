# PTUM Pesta Tanglung Hand-Swipe Map

An interactive hand-swipe map created by the Multimedia and Technical Team for the PTUM Pesta Tanglung exhibition at Universiti Malaya.

The application is designed to run beside a projector. Visitors can move their hand or arm in front of a camera to browse through the exhibition map before walking into the exhibition area. Each map page is displayed like a digital book, with a page-flip animation between screens. Static images and animated GIF pages are supported.

## What This Project Does

- Opens the pages stored in the `pages/` folder.
- Displays the current page in an OpenCV window.
- Uses the camera to detect the participant's body pose and arm movement.
- Detects horizontal swipe movement without requiring a touchscreen or mouse.
- Moves to the next or previous map page with an animated transition.
- Supports animated GIF pages.
- Can display the map window in fullscreen for a projector.

## Technology Used

- **Python**: Main programming language.
- **OpenCV**: Camera input, image processing, display windows, resizing, fullscreen mode, and page-flip animation.
- **MediaPipe Hands**: Hand landmark detection and drawing utilities.
- **MediaPipe Pose**: Tracks the shoulder, elbow, and wrist to measure arm movement relative to the participant's body.
- **NumPy**: Image-frame and canvas manipulation.
- **Pillow (PIL)**: Loads animated GIF files frame by frame.

## Requirements

- macOS with Python 3.9 or newer recommended.
- A working webcam or USB camera.
- A projector connected to the computer.
- Good lighting around the interaction area.
- Enough space for participants to move one arm horizontally in front of the camera.

## Setup

Open Terminal and move into the project folder:

```bash
cd /Users/gohshengfung/Documents/Projects/bookFlipPTUM
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the required Python packages:

```bash
python -m pip install --upgrade pip
python -m pip install opencv-python mediapipe numpy pillow
```

## Running the Application

Make sure the virtual environment is active, then run:

```bash
python handswipe.py
```

## Exhibition Controls

| Action | Result |
| --- | --- |
| Swipe left | Go to the next page |
| Swipe right | Go to the previous page |
| Press `F` | Toggle projector window fullscreen |
| Press `Esc` | Exit the application |

The application opens two windows:

- **Book**: The map intended for the projector.
- **Camera**: The camera feed and pose-detection status used for setup and troubleshooting.

For the exhibition, place the **Book** window on the projector display and press `F` while that window is active. The camera window can remain on the laptop or operator display.

## Adding or Updating Map Pages

Put supported image files in the `pages/` folder:

- `.png`
- `.jpg` or `.jpeg`
- `.gif`

Pages are loaded in alphabetical order by filename. Rename files with a numeric prefix when a specific order is important, for example:

```text
pages/
  page1.png
  page2.gif
  page3.gif
  page4.gif
```

Images and GIF frames are resized to `1280 x 720` when the program starts. Prepare map artwork in a 16:9 layout where possible to reduce unwanted stretching.

## Camera and Projector Setup

1. Connect the webcam and projector before starting the program.
2. Give Terminal or Python camera access when macOS requests permission. This can be reviewed in **System Settings > Privacy & Security > Camera**.
3. Position the camera so the participant's upper body and moving arm are visible.
4. Keep the camera steady and avoid strong backlighting.
5. Start the program and confirm that the camera feed shows `Hand: READY` when an arm is visible.
6. Test both swipe directions before opening the exhibition.
7. Move the **Book** window to the projector and press `F` for fullscreen.

## Troubleshooting

### Camera does not open

- Check that the webcam is connected and not being used by another application.
- Allow camera access for Terminal or the application running Python in macOS settings.
- Restart the program after changing camera permissions.

### Swipe is not detected

- Move one arm horizontally and clearly across the camera view.
- Make sure the shoulders, elbow, and wrist are visible.
- Improve the lighting and reduce visual obstruction behind the participant.
- Keep the camera at a suitable distance so the upper body is visible.

### Projector shows the wrong window

- Move the **Book** window to the projector display.
- Click the **Book** window before pressing `F`.
- Press `F` again to leave fullscreen mode if the window needs to be moved.

### GIF pages are not animated

- Confirm that the file extension is `.gif`.
- Confirm that the GIF can be opened normally on the computer.
- Restart the application after replacing a page file.

## Project Structure

```text
bookFlipPTUM/
├── handswipe.py       # Main interactive application
├── pages/             # Map images and animated pages
│   ├── page1.png
│   ├── page2.gif
│   ├── page3.gif
│   └── page4.gif
└── README.md          # Project documentation
```

## Team and Exhibition Context

This project is part of the Multimedia and Technical Team's interactive exhibition setup for PTUM Pesta Tanglung, Universiti Malaya. Its purpose is to give participants a simple, contactless way to preview the exhibition map before entering the exhibition area.