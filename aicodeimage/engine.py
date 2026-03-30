import os
import cv2
import json
import shutil
from pathlib import Path
import face_recognition
import persons as person_mgr

# Restrict to Media only
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VID_EXT = {".mp4", ".avi", ".mov", ".mkv"}
ALL_EXTS = IMG_EXT | VID_EXT

class Config:
    mode = "soft"  # 'soft' (database only) or 'hard' (physical copy)
    tolerance = 0.6 # Face matching strictness (lower is stricter)
    frame_skip = 30 # For videos: check 1 frame every X frames to save time

CFG = Config()

def process_media(filepath, known_persons):
    """
    Scans media, identifies faces, adds unknown faces to the database.
    Returns a list of identified person names.
    """
    ext = Path(filepath).suffix.lower()
    found_names = set()
    
    if ext in IMG_EXT:
        image = face_recognition.load_image_file(filepath)
        found_names.update(_detect_faces_in_image(image, known_persons))
        
    elif ext in VID_EXT:
        video_capture = cv2.VideoCapture(str(filepath))
        frame_count = 0
        while True:
            ret, frame = video_capture.read()
            if not ret:
                break
            
            # Process every Nth frame to save time
            if frame_count % CFG.frame_skip == 0:
                # Convert OpenCV BGR format to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                found_names.update(_detect_faces_in_image(rgb_frame, known_persons))
            frame_count += 1
            
        video_capture.release()
        
    return list(found_names)

def _detect_faces_in_image(rgb_image, known_persons):
    """Helper to extract encodings and match against known persons."""
    found_names = set()
    face_locations = face_recognition.face_locations(rgb_image)
    face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
    
    # Prepare lists for comparison
    known_encodings = []
    known_ids = []
    for pid, info in known_persons.items():
        for enc in info["encodings"]:
            known_encodings.append(enc)
            known_ids.append(pid)

    for face_encoding in face_encodings:
        if not known_encodings:
            # First face ever detected!
            new_id, new_name = person_mgr.add_new_person(known_persons, face_encoding)
            found_names.add(new_name)
            known_encodings.append(face_encoding)
            known_ids.append(new_id)
            continue
            
        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=CFG.tolerance)
        
        if True in matches:
            first_match_index = matches.index(True)
            matched_id = known_ids[first_match_index]
            found_names.add(known_persons[matched_id]["name"])
        else:
            # Unknown face detected
            new_id, new_name = person_mgr.add_new_person(known_persons, face_encoding)
            found_names.add(new_name)
            known_encodings.append(face_encoding)
            known_ids.append(new_id)
            
    return found_names

def run(sources, dest_dir):
    """Main batch processor"""
    known_persons = person_mgr.load_persons()
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)
    
    report = []
    
    for src in sources:
        for root, _, files in os.walk(src):
            for file in files:
                filepath = Path(root) / file
                if filepath.suffix.lower() not in ALL_EXTS:
                    continue
                
                detected_people = process_media(filepath, known_persons)
                
                if not detected_people:
                    detected_people = ["No_Faces_Detected"]
                
                # Handle Hard/Soft Mode Action
                for person_name in detected_people:
                    safe_name = person_name.replace(" ", "_")
                    
                    if CFG.mode == "hard":
                        person_dir = dest_path / safe_name
                        person_dir.mkdir(exist_ok=True)
                        shutil.copy2(filepath, person_dir / filepath.name)
                        
                # Log for Soft mode report
                report.append({
                    "file": str(filepath),
                    "people": detected_people
                })

    # Save the soft mode database
    (dest_path / "media_scan_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")