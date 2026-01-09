import cv2
import mediapipe as mp
import numpy as np
import os
from PIL import Image

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.2
)

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.3
)

mp_draw = mp.solutions.drawing_utils

def load_image(filepath):
    """Load image from file, supporting PNG, JPG, and GIF formats"""
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext == '.gif':
        # Load all frames from GIF
        gif = Image.open(filepath)
        frames = []
        try:
            while True:
                frame = np.array(gif.convert('RGB'))
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                frames.append(frame)
                gif.seek(gif.tell() + 1)
        except EOFError:
            pass  # End of GIF
        
        # Get GIF duration per frame (in milliseconds)
        try:
            duration = gif.info.get('duration', 100)  # Default 100ms if not specified
        except:
            duration = 100
            
        return {'type': 'gif', 'frames': frames, 'duration': duration, 'current_frame': 0}
    else:
        # Load PNG, JPG, JPEG, etc. with OpenCV
        img = cv2.imread(filepath)
        return {'type': 'static', 'image': img}

PAGE_FOLDER = "pages"
# Filter for image files only (png, jpg, jpeg, gif)
all_files = os.listdir(PAGE_FOLDER)
image_files = [f for f in all_files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
pages = sorted([os.path.join(PAGE_FOLDER, p) for p in image_files])

book_pages = [load_image(p) for p in pages]
current_page = 0

SCREEN_W, SCREEN_H = 1280, 720

# Resize all images/frames to screen size
for page in book_pages:
    if page['type'] == 'gif':
        page['frames'] = [cv2.resize(f, (SCREEN_W, SCREEN_H)) for f in page['frames']]
    else:
        page['image'] = cv2.resize(page['image'], (SCREEN_W, SCREEN_H))

# Frame counter for GIF animation
gif_frame_counter = 0

prev_x = None
SWIPE_THRESHOLD = 80  # Reduced for more sensitive detection
cooldown = 0
COOLDOWN_FRAMES = 20  # About 0.67 seconds at 30fps
swipe_message = ""
message_timer = 0
hand_stable_frames = 0
MIN_STABLE_FRAMES = 0  # Start tracking immediately - no delay
accumulated_movement = 0
movement_direction = 0  # 1 for right, -1 for left, 0 for none
JITTER_THRESHOLD = 3  # Lower threshold for relative positioning
hand_lost_buffer = 0
MAX_HAND_LOST_FRAMES = 2  # Allow 2 frames of hand not detected before resetting
tracked_wrist = None  # Track which wrist we're following ("left" or "right")
smoothed_x = None  # Smoothed position to reduce jitter

def get_current_frame(page_data):
    """Get the current frame to display for a page (handles both static images and GIFs)"""
    if page_data['type'] == 'gif':
        return page_data['frames'][page_data['current_frame']]
    else:
        return page_data['image']

def flip_animation(current_page_data, next_page_data, direction="next"):
    for i in range(20):
        alpha = i / 20

        # Get current frames from both pages
        current = get_current_frame(current_page_data)
        next_page = get_current_frame(next_page_data)

        if direction == "next":
            # Flip from right: current page shrinks from right, next appears from left
            w_current = int(SCREEN_W * (1 - alpha))
            w_next = int(SCREEN_W * alpha)
        else:
            # Flip from left: current page shrinks from left, next appears from right
            w_current = int(SCREEN_W * (1 - alpha))
            w_next = int(SCREEN_W * alpha)

        if w_current <= 0:
            w_current = 1
        if w_next <= 0:
            w_next = 1

        temp_current = cv2.resize(current, (w_current, SCREEN_H))
        temp_next = cv2.resize(next_page, (w_next, SCREEN_H))
        canvas = np.zeros((SCREEN_H, SCREEN_W, 3), dtype=np.uint8)

        if direction == "next":
            # Current page on right (shrinking), next page on left (growing)
            canvas[:, SCREEN_W-w_current:] = temp_current
            canvas[:, :w_next] = temp_next
        else:
            # Current page on left (shrinking), next page on right (growing)
            canvas[:, :w_current] = temp_current
            canvas[:, SCREEN_W-w_next:] = temp_next

        cv2.imshow("Book", canvas)
        cv2.waitKey(15)

# Camera PORT IS HERE
cap = cv2.VideoCapture(0)

# Create windows with fullscreen capability
cv2.namedWindow("Camera", cv2.WINDOW_NORMAL)
cv2.namedWindow("Book", cv2.WINDOW_NORMAL)

# Variable to track fullscreen state
is_fullscreen = False

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    hand_result = hands.process(rgb)
    pose_result = pose.process(rgb)
    
    # Update GIF animation
    gif_frame_counter += 1
    current_page_data = book_pages[current_page]
    if current_page_data['type'] == 'gif':
        # Update frame every few iterations based on GIF duration
        frames_per_gif_frame = max(1, int(current_page_data['duration'] / 33))  # Assuming ~30fps
        if gif_frame_counter % frames_per_gif_frame == 0:
            current_page_data['current_frame'] = (current_page_data['current_frame'] + 1) % len(current_page_data['frames'])
    
    # Decrement cooldown FIRST before any detection
    if cooldown > 0:
        cooldown -= 1
    
    if message_timer > 0:
        message_timer -= 1
    else:
        swipe_message = ""

    hand_detected = False
    movement_diff = 0

    # Track ARM movement RELATIVE TO BODY (shoulder as reference)
    relative_arm_x = None
    current_wrist = None
    if pose_result.pose_landmarks:
        # Get shoulders (right 12, left 11), elbows (right 14, left 13), wrists (right 16, left 15)
        right_shoulder = pose_result.pose_landmarks.landmark[12]
        left_shoulder = pose_result.pose_landmarks.landmark[11]
        right_elbow = pose_result.pose_landmarks.landmark[14]
        left_elbow = pose_result.pose_landmarks.landmark[13]
        right_wrist = pose_result.pose_landmarks.landmark[16]
        left_wrist = pose_result.pose_landmarks.landmark[15]
        
        # Prioritize the arm we're already tracking
        if tracked_wrist == "right" and right_wrist.visibility > 0.3 and right_shoulder.visibility > 0.5:
            shoulder_x = right_shoulder.x * SCREEN_W
            # Weighted arm position (wrist 60%, elbow 40%)
            if right_elbow.visibility > 0.3:
                arm_x = (0.6 * right_wrist.x + 0.4 * right_elbow.x) * SCREEN_W
            else:
                arm_x = right_wrist.x * SCREEN_W
            # Calculate position RELATIVE to shoulder (this is distance independent!)
            relative_arm_x = arm_x - shoulder_x
            current_wrist = "right"
            hand_detected = True
            
        elif tracked_wrist == "left" and left_wrist.visibility > 0.3 and left_shoulder.visibility > 0.5:
            shoulder_x = left_shoulder.x * SCREEN_W
            # Weighted arm position (wrist 60%, elbow 40%)
            if left_elbow.visibility > 0.3:
                arm_x = (0.6 * left_wrist.x + 0.4 * left_elbow.x) * SCREEN_W
            else:
                arm_x = left_wrist.x * SCREEN_W
            # Calculate position RELATIVE to shoulder
            relative_arm_x = arm_x - shoulder_x
            current_wrist = "left"
            hand_detected = True
            
        # If no tracked arm, pick the most visible one
        elif (right_wrist.visibility > 0.4 and right_shoulder.visibility > 0.5) or \
             (left_wrist.visibility > 0.4 and left_shoulder.visibility > 0.5):
            if right_wrist.visibility > left_wrist.visibility:
                shoulder_x = right_shoulder.x * SCREEN_W
                if right_elbow.visibility > 0.3:
                    arm_x = (0.6 * right_wrist.x + 0.4 * right_elbow.x) * SCREEN_W
                else:
                    arm_x = right_wrist.x * SCREEN_W
                relative_arm_x = arm_x - shoulder_x
                current_wrist = "right"
            else:
                shoulder_x = left_shoulder.x * SCREEN_W
                if left_elbow.visibility > 0.3:
                    arm_x = (0.6 * left_wrist.x + 0.4 * left_elbow.x) * SCREEN_W
                else:
                    arm_x = left_wrist.x * SCREEN_W
                relative_arm_x = arm_x - shoulder_x
                current_wrist = "left"
            hand_detected = True
    
    # NO fallback to hand landmarks - we ONLY track arm movement relative to body
    
    if relative_arm_x is not None:
        # Apply light smoothing to reduce jitter
        if smoothed_x is None:
            smoothed_x = relative_arm_x
        else:
            # Smooth with 85% current, 15% previous (less dampening)
            smoothed_x = int(0.85 * relative_arm_x + 0.15 * smoothed_x)
        
        x = smoothed_x
        tracked_wrist = current_wrist  # Remember which arm we're tracking

        hand_stable_frames += 1

        # Skip movement detection if in cooldown
        if prev_x is not None and cooldown == 0 and hand_stable_frames >= MIN_STABLE_FRAMES:
            diff = x - prev_x
            movement_diff = diff
            
            # Detect movement direction
            if abs(diff) > JITTER_THRESHOLD:  # Ignore hand jitter
                current_direction = 1 if diff > 0 else -1
                
                # If direction changed, reset accumulated movement
                if movement_direction != 0 and current_direction != movement_direction:
                    accumulated_movement = 0
                
                movement_direction = current_direction
                accumulated_movement += abs(diff)
            
            # Check if accumulated movement exceeds threshold
            if accumulated_movement > SWIPE_THRESHOLD:
                if movement_direction > 0:  # Swiped right
                    # Swipe right - go to previous page (loop to last page if at first)
                    next_page = (current_page - 1) % len(book_pages)
                    
                    # Reset ALL state BEFORE animation to prevent double detection
                    cooldown = COOLDOWN_FRAMES
                    accumulated_movement = 0
                    movement_direction = 0
                    hand_stable_frames = 0
                    prev_x = None
                    hand_lost_buffer = 0
                    
                    flip_animation(book_pages[current_page], book_pages[next_page], "next")
                    current_page = next_page
                    swipe_message = "SWIPED RIGHT - Previous Page"
                    message_timer = 30
                    continue  # Skip rest of frame processing

                elif movement_direction < 0:  # Swiped left
                    # Swipe left - go to next page (loop to first page if at last)
                    next_page = (current_page + 1) % len(book_pages)
                    
                    # Reset ALL state BEFORE animation to prevent double detection
                    cooldown = COOLDOWN_FRAMES
                    accumulated_movement = 0
                    movement_direction = 0
                    hand_stable_frames = 0
                    prev_x = None
                    hand_lost_buffer = 0
                    
                    flip_animation(book_pages[current_page], book_pages[next_page], "prev")
                    current_page = next_page
                    swipe_message = "SWIPED LEFT - Next Page"
                    message_timer = 30
                    continue  # Skip rest of frame processing

        # Only update prev_x if no swipe was triggered
        prev_x = x
        
        # Draw landmarks
        if hand_result.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, hand_result.multi_hand_landmarks[0], mp_hands.HAND_CONNECTIONS)
        if pose_result.pose_landmarks:
            mp_draw.draw_landmarks(frame, pose_result.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        
        hand_lost_buffer = 0  # Reset buffer when hand is detected
    else:
        # Use buffer before resetting - allow brief hand loss during fast swipe
        hand_lost_buffer += 1
        if hand_lost_buffer > MAX_HAND_LOST_FRAMES:
            # Reset only after hand lost for several frames
            hand_stable_frames = 0
            prev_x = None
            accumulated_movement = 0
            movement_direction = 0
            tracked_wrist = None  # Reset wrist tracking
            smoothed_x = None  # Reset smoothing
    
    # Enforce cooldown state throughout frame
    if cooldown > 0:
        accumulated_movement = 0
        movement_direction = 0
        hand_stable_frames = 0
    
    # Display info on camera feed
    cv2.putText(frame, f"Page: {current_page + 1}/{len(book_pages)}", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    if hand_detected:
        status_color = (0, 255, 0) if hand_stable_frames >= MIN_STABLE_FRAMES else (255, 165, 0)
        status_text = "Hand: READY" if hand_stable_frames >= MIN_STABLE_FRAMES else f"Hand: STABILIZING ({hand_stable_frames}/{MIN_STABLE_FRAMES})"
        cv2.putText(frame, status_text, (10, 70), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
    else:
        cv2.putText(frame, "Hand: NOT DETECTED", (10, 70), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    if swipe_message:
        cv2.putText(frame, swipe_message, (10, 110), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
    
    if cooldown > 0:
        cv2.putText(frame, f"Cooldown: {cooldown}", (10, 150), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    
    # Show movement delta and hand position for debugging
    if hand_detected:
        direction_text = "→ RIGHT" if movement_direction > 0 else "← LEFT" if movement_direction < 0 else "NONE"
        cv2.putText(frame, f"Accumulated: {int(accumulated_movement)}/{SWIPE_THRESHOLD} ({direction_text})", (10, 190), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        if prev_x is not None:
            cv2.putText(frame, f"Hand X: {prev_x}", (10, 230), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    cv2.imshow("Camera", frame)
    cv2.imshow("Book", get_current_frame(book_pages[current_page]))

    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC to exit
        break
    elif key == ord('f') or key == ord('F'):  # Press 'f' to toggle fullscreen
        is_fullscreen = not is_fullscreen
        if is_fullscreen:
            cv2.setWindowProperty("Book", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        else:
            cv2.setWindowProperty("Book", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)

cap.release()
cv2.destroyAllWindows()
