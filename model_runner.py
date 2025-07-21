#model_runner
import torch
import json
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import argparse
import sys
import os
import time
import re

class HouseModelInference:
    def __init__(self, model_path, device=None):
        """Initialize the model for house layout generation from text description."""
        self.model_path = model_path
        self.max_length = 256  # From training script (adjust if needed)
        self.max_target_length = 512  # From training script (adjust if needed)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        # Load tokenizer and model
        print(f"Loading model from {model_path}...")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(model_path)
            self.model.to(self.device)
            print(f"Model loaded successfully on {self.device}")
        except Exception as e:
            print(f"Error loading model: {e}")
            sys.exit(1)

    def generate_house_text(self, text_description):
        """Generate raw house text from natural language description."""
        print(f"Generating house layout for: '{text_description[:100]}...'")

        # Prepare input
        inputs = self.tokenizer(
            text_description,
            return_tensors="pt",
            padding="max_length",
            max_length=self.max_length,
            truncation=True
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Generate output text
        try:
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=self.max_target_length,
                    num_beams=2,
                    early_stopping=True
                )

            # Get the raw text output
            raw_text = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
            return raw_text
        except Exception as e:
            print(f"Error during generation: {e}")
            return None

def fix_json_string(raw_text):
    """Attempt to fix common JSON formatting issues in the model output."""
    # Check if the string already has proper JSON formatting
    if raw_text.strip().startswith('{') and raw_text.strip().endswith('}'):
        return raw_text
    
    # Fix missing opening brace
    if raw_text.strip().startswith('"id"') or raw_text.strip().startswith('"numRooms"'):
        raw_text = '{' + raw_text
    
    # Fix missing closing brace
    if not raw_text.strip().endswith('}'):
        raw_text = raw_text + '}'
    
    # Fix missing quotes around keys
    def add_quotes_to_keys(match):
        key = match.group(1)
        return f'"{key}":'
    
    raw_text = re.sub(r'([a-zA-Z0-9_]+):', add_quotes_to_keys, raw_text)
    
    # Fix missing commas between objects in arrays
    raw_text = re.sub(r'}\s*{', '}, {', raw_text)
    raw_text = re.sub(r'"\s*{', '", {', raw_text)
    raw_text = re.sub(r'}\s*"', '}, "', raw_text)
    
    return raw_text

def save_text_file(text, file_path):
    """Save text data to file with proper error handling."""
    try:
        # Create directory if it doesn't exist
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        # Save the file
        with open(file_path, 'w') as f:
            f.write(text)

        print(f"Successfully saved output to: {file_path}")
        return True  # Indicate success

    except Exception as e:
        print(f"Error saving file to {file_path}: {e}")
        fallback_path = f"house_output_raw_{int(time.time())}.txt"
        try:
            with open(fallback_path, 'w') as f:
                f.write(text)
            print(f"Saved fallback file to: {fallback_path}")
            return True  # Indicate success even with fallback
        except Exception as fallback_e:
            print(f"Failed to save even to fallback location: {fallback_e}")
            return False  # Indicate complete failure

def attempt_json_parse(text):
    """Try to parse text as JSON, return None if it fails."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Generate house layout from text description")
    parser.add_argument("--model_path", type=str, required=True, help="Path to the trained model directory")
    parser.add_argument("--description", type=str, help="Text description of house layout")
    parser.add_argument("--output_raw", type=str, default="generated_house_raw.txt",
                        help="Output file path for raw text (default: generated_house_raw.txt)")
    parser.add_argument("--output_json", type=str, default="generated_house.json",
                        help="Output file path for JSON (default: generated_house.json)")

    args = parser.parse_args()

    # Initialize model
    model = HouseModelInference(args.model_path)

    # Get input text
    description = args.description if args.description else input("Enter house description: ")

    # Generate house raw text
    raw_text = model.generate_house_text(description)

    if not raw_text:
        print("Failed to generate house layout text.")
        return 1

    # Save raw output regardless of JSON validity
    print("\nRaw output preview:")
    print(raw_text[:200] + "..." if len(raw_text) > 200 else raw_text)
    raw_text_saved = save_text_file(raw_text, args.output_raw)  # Capture the return value
    if not raw_text_saved:
        print("Failed to save raw output. Exiting.")
        return 1

    print(f"Complete raw output saved to {args.output_raw}")

    # Try to fix and parse JSON
    fixed_json_text = fix_json_string(raw_text)
    json_obj = attempt_json_parse(fixed_json_text)

    if json_obj:
        print("\nSuccessfully parsed JSON after fixing format!")
        # Save the fixed JSON
        json_saved = save_text_file(json.dumps(json_obj, indent=2), args.output_json)  # Capture the return value
        if json_saved:
            print(f"Fixed JSON saved to {args.output_json}")
            return 0
        else:
            print(f"Failed to save fixed JSON to {args.output_json}")
            return 1
    else:
        print("\nCould not automatically fix JSON format.")
        print("You can try to manually fix the raw output saved in the text file.")

        # Save the attempted fixed version too, for debugging
        save_text_file(fixed_json_text, args.output_json + ".attempted_fix.txt")
        print(f"Attempted fixed version saved to {args.output_json}.attempted_fix.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())