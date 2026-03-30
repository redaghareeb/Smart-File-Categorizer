import json
import numpy as np
from pathlib import Path

PERSONS_FILE = Path.home() / ".smart_media_persons.json"

def load_persons():
    """
    Loads persons and their face encodings from JSON.
    Returns: { "person_id": {"name": "John", "encodings": [np.array, ...]} }
    """
    if not PERSONS_FILE.exists():
        return {}
    
    try:
        data = json.loads(PERSONS_FILE.read_text(encoding="utf-8"))
        # Convert lists back to numpy arrays for the face_recognition library
        for pid in data:
            data[pid]["encodings"] = [np.array(enc) for enc in data[pid]["encodings"]]
        return data
    except Exception as e:
        print(f"Error loading persons: {e}")
        return {}

def save_persons(persons_dict):
    """
    Saves persons to JSON. Converts numpy arrays to lists for serialization.
    """
    try:
        data_to_save = {}
        for pid, info in persons_dict.items():
            data_to_save[pid] = {
                "name": info["name"],
                "encodings": [enc.tolist() for enc in info["encodings"]]
            }
        PERSONS_FILE.write_text(json.dumps(data_to_save, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"Error saving persons: {e}")

def add_new_person(persons_dict, encoding, name_prefix="Person"):
    """
    Registers a new unknown person.
    """
    person_count = len(persons_dict) + 1
    new_id = f"person_{person_count}"
    new_name = f"{name_prefix} {person_count}"
    
    persons_dict[new_id] = {
        "name": new_name,
        "encodings": [encoding]
    }
    save_persons(persons_dict)
    return new_id, new_name

def update_person_name(persons_dict, person_id, new_name):
    """Updates the display name of a person."""
    if person_id in persons_dict:
        persons_dict[person_id]["name"] = new_name
        save_persons(persons_dict)
    return persons_dict