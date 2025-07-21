#Validator
import json
import os
import re
import logging
import numpy as np
import random
from json.decoder import JSONDecodeError
from typing import Dict, List, Union, Any, Optional, Tuple
from collections import defaultdict, Counter
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ProcTHORValidator")

class ProcTHORValidator:
    def __init__(self, template_file="procthor_10k.jsonl"):
        self.template_file = template_file
        self.templates = self._load_templates()
        self.vectorizer = TfidfVectorizer(stop_words=stopwords.words('english'))
        self.text_features = self._extract_all_text_features()
        
        # Create dictionary for room keyword mapping
        self.room_keywords = {
            "kitchen": ["kitchen", "dining", "cook", "food", "meal", "eat", "counter", "sink", "stove", "fridge", "refrigerator", "oven", "microwave"],
            "bathroom": ["bathroom", "bath", "toilet", "shower", "tub", "sink", "washroom", "restroom", "wc"],
            "bedroom": ["bedroom", "bed", "sleep", "rest", "dresser", "nightstand"],
            "living": ["living", "family", "sitting", "lounge", "tv", "sofa", "couch", "entertainment"],
            "hallway": ["hallway", "corridor", "passage", "hall", "entryway", "entry"],
            "office": ["office", "study", "work", "desk", "computer", "home office"],
            "closet": ["closet", "storage", "wardrobe"]
        }
        
        # Create dictionary for object keyword mapping
        self.object_keywords = {
            "furniture": ["table", "chair", "sofa", "couch", "bed", "dresser", "cabinet", "shelf", "desk", "bookshelf"],
            "appliance": ["fridge", "refrigerator", "oven", "stove", "microwave", "dishwasher", "washer", "dryer", "tv", "television"],
            "fixture": ["sink", "toilet", "shower", "tub", "bathtub", "faucet", "light", "lamp", "ceiling fan"],
            "decor": ["rug", "carpet", "painting", "picture", "mirror", "plant", "curtain", "blind", "vase"]
        }
        
        # Extract room and object counts per template for faster scoring
        self._analyze_templates()
        
    def _load_templates(self) -> List[Dict]:
        """Load templates from JSON Lines file (one JSON per line)"""
        templates = []
        if not os.path.exists(self.template_file):
            logger.error(f"Template file {self.template_file} not found!")
            return templates

        try:
            with open(self.template_file, 'r') as f:
                for line_number, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue  # Skip empty lines

                    try:
                        template = json.loads(line)
                        templates.append(template)
                        if len(templates) >= 10000:
                            break  # Limit to first 10k templates
                    except JSONDecodeError as e:
                        logger.warning(f"Error parsing line {line_number}: {str(e)}")
                    except Exception as e:
                        logger.warning(f"Error processing line {line_number}: {str(e)}")

            logger.info(f"Loaded {len(templates)} templates from {self.template_file}")
            return templates
        except Exception as e:
            logger.error(f"Failed to load templates: {str(e)}")
            return []
    
    def _analyze_templates(self):
        """Analyze templates to extract room and object counts for faster matching"""
        self.template_features = []
        
        for template in self.templates:
            features = {}
            house = template.get('house_json', {})
            
            # Count rooms by type
            room_counts = Counter()
            for room in house.get('rooms', []):
                room_type = room.get('roomType', '').lower()
                room_counts[room_type] += 1
            
            # Count objects by type
            object_counts = Counter()
            for obj in house.get('objects', []):
                obj_type = obj.get('objectType', '').lower()
                object_counts[obj_type] += 1
            
            # Basic structure counts
            features['total_rooms'] = len(house.get('rooms', []))
            features['total_objects'] = len(house.get('objects', []))
            features['total_doors'] = len(house.get('doors', []))
            features['total_windows'] = len(house.get('windows', []))
            
            # Room counts by type
            features['room_counts'] = dict(room_counts)
            
            # Object counts by type
            features['object_counts'] = dict(object_counts)
            
            # Add to template features list
            self.template_features.append(features)
        
        logger.info(f"Analyzed {len(self.template_features)} templates")

    def _extract_all_text_features(self) -> List[str]:
        """Extract text descriptions from templates for text-based similarity"""
        if not self.templates:
            return []
        return [template.get('nl_description', '') for template in self.templates]

    def _extract_keywords_and_counts(self, input_text: str) -> Tuple[Dict[str, int], Dict[str, int], Dict[str, int]]:
        """
        Extract keywords and numeric values from input text
        Returns:
            - room_counts: Dictionary of room types and their counts
            - object_counts: Dictionary of object types and their counts
            - numeric_values: Dictionary of numeric attributes (floors, dimensions, etc.)
        """
        # Clean and normalize input text
        text = input_text.lower()
        
        # Extract numbers with context
        numeric_values = {}
        
        # Look for number of rooms
        room_count_patterns = [
            r'(\d+)\s*rooms?',
            r'rooms?[\s:]+(\d+)',
            r'numrooms?[\s:]+(\d+)',
            r'number\s+of\s+rooms?[\s:]+(\d+)'
        ]
        
        for pattern in room_count_patterns:
            match = re.search(pattern, text)
            if match:
                numeric_values['total_rooms'] = int(match.group(1))
                break
        
        # Look for number of floors
        floor_patterns = [
            r'(\d+)\s*floors?',
            r'floors?[\s:]+(\d+)',
            r'numfloors?[\s:]+(\d+)',
            r'number\s+of\s+floors?[\s:]+(\d+)',
            r'stories?[\s:]+(\d+)',
            r'(\d+)\s*stor(?:ies|ys?)'
        ]
        
        for pattern in floor_patterns:
            match = re.search(pattern, text)
            if match:
                numeric_values['floors'] = int(match.group(1))
                break
        
        # Look for dimensions
        dimension_patterns = [
            r'dimensions?[\s:]+(\d+)[^\d]*(\d+)',
            r'size[\s:]+(\d+)[^\d]*(\d+)',
            r'(\d+)\s*[xX]\s*(\d+)',
            r'width[\s:]+(\d+)',
            r'length[\s:]+(\d+)'
        ]
        
        for pattern in dimension_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    if len(match.groups()) >= 2:
                        numeric_values['width'] = int(match.group(1))
                        numeric_values['length'] = int(match.group(2))
                    else:
                        numeric_values['dimension'] = int(match.group(1))
                except (ValueError, IndexError):
                    pass
                break
        
        # Extract room types and counts
        room_counts = defaultdict(int)
        
        # First look for explicit room counts
        room_type_patterns = {
            "kitchen": [r'(\d+)\s*kitchens?', r'kitchens?[\s:]+(\d+)'],
            "bedroom": [r'(\d+)\s*bedrooms?', r'bedrooms?[\s:]+(\d+)'],
            "bathroom": [r'(\d+)\s*bathrooms?', r'bathrooms?[\s:]+(\d+)'],
            "living": [r'(\d+)\s*living\s*rooms?', r'living\s*rooms?[\s:]+(\d+)']
        }
        
        for room_type, patterns in room_type_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        room_counts[room_type] = int(match.group(1))
                    except (ValueError, IndexError):
                        room_counts[room_type] = 1
                    break
        
        # Then check for mentions without explicit counts
        for room_type, keywords in self.room_keywords.items():
            if room_type not in room_counts:  # Only if not already found with count
                for keyword in keywords:
                    if re.search(r'\b' + re.escape(keyword) + r'\b', text):
                        room_counts[room_type] = 1
                        break
        
        # Extract object types and counts
        object_counts = defaultdict(int)
        
        # Common objects and their patterns
        object_type_patterns = {
            "table": [r'(\d+)\s*tables?', r'tables?[\s:]+(\d+)'],
            "chair": [r'(\d+)\s*chairs?', r'chairs?[\s:]+(\d+)'],
            "sofa": [r'(\d+)\s*sofas?', r'sofas?[\s:]+(\d+)'],
            "bed": [r'(\d+)\s*beds?', r'beds?[\s:]+(\d+)'],
            "sink": [r'(\d+)\s*sinks?', r'sinks?[\s:]+(\d+)'],
            "toilet": [r'(\d+)\s*toilets?', r'toilets?[\s:]+(\d+)']
        }
        
        for obj_type, patterns in object_type_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        object_counts[obj_type] = int(match.group(1))
                    except (ValueError, IndexError):
                        object_counts[obj_type] = 1
                    break
        
        # Then scan for simple mentions
        for category, keywords in self.object_keywords.items():
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', text):
                    if keyword not in object_counts:
                        object_counts[keyword] = 1
        
        return room_counts, object_counts, numeric_values

    def _score_template(self, 
                    template_idx: int, 
                    room_counts: Dict[str, int], 
                    object_counts: Dict[str, int], 
                    numeric_values: Dict[str, int]) -> float:
        """
        Modified scoring function that:
        1. Heavily prioritizes matching room counts
        2. Penalizes templates with too few rooms/objects compared to input
        3. Uses template index in scoring to break ties
        4. Adds randomization factor to prevent always selecting the same templates
        
        Returns a score between 0 (no match) and 1 (perfect match)
        """
        template_features = self.template_features[template_idx]
        score = 0.0
        total_weight = 0.0
        
        # Apply a small random factor (1-5%) to break ties
        random_factor = 1.0 + (random.random() * 0.04)
        
        # === ROOM COUNT MATCHING (HIGHEST PRIORITY) ===
        if 'total_rooms' in numeric_values:
            weight = 10.0  # Increased from 5.0
            total_weight += weight
            template_rooms = template_features['total_rooms']
            target_rooms = numeric_values['total_rooms']
            
            # Perfect match gets full score
            if template_rooms == target_rooms:
                score += weight
            # Close match gets partial score
            elif abs(template_rooms - target_rooms) == 1:
                score += 0.7 * weight
            elif abs(template_rooms - target_rooms) == 2:
                score += 0.4 * weight
            # Heavily penalize templates with fewer rooms than requested
            elif template_rooms < target_rooms:
                score -= 0.5 * weight  # Negative score for missing rooms
            # Small penalty for having too many rooms
            else:
                score += 0.2 * weight
        
        # === ROOM TYPE MATCHING ===
        for room_type, count in room_counts.items():
            weight = 5.0  # Increased from 3.0
            total_weight += weight
            template_count = template_features['room_counts'].get(room_type, 0)
            
            # Perfect match gets full score
            if template_count == count:
                score += weight
            # Partial matches get proportional scores
            elif template_count > 0 and count > 0:
                # Calculate proportion of matched rooms
                match_ratio = min(template_count, count) / max(template_count, count)
                score += match_ratio * weight
            # Penalize missing room types that were specifically requested
            elif template_count == 0 and count > 0:
                score -= 0.3 * weight  # Negative score for missing room types
        
        # === OBJECT MATCHING ===
        # Track how many requested objects are present
        object_match_score = 0
        object_match_count = 0
        
        for obj_type, count in object_counts.items():
            weight = 2.0  # Increased from 1.0
            total_weight += weight
            template_count = template_features['object_counts'].get(obj_type, 0)
            
            # Perfect or excess object count
            if template_count >= count:
                object_match_score += weight
            # Partial object presence
            elif template_count > 0:
                match_ratio = template_count / count
                object_match_score += match_ratio * weight
            # Missing objects that were requested
            else:
                object_match_score -= 0.2 * weight  # Penalty for missing objects
            
            object_match_count += 1
        
        # Add object matching score if we checked any objects
        if object_match_count > 0:
            score += object_match_score
        
        # === OTHER STRUCTURAL FEATURES ===
        # Match on floors if specified
        if 'floors' in numeric_values:
            weight = 4.0
            total_weight += weight
            
            # We don't have floors in template_features, so we'll need to add this
            # For now, assume single floor if not specified
            template_floors = 1  # This should be extracted from the template in a real implementation
            target_floors = numeric_values['floors']
            
            if template_floors == target_floors:
                score += weight
            elif abs(template_floors - target_floors) == 1:
                score += 0.5 * weight
        
        # === ENSURE DIVERSE SELECTIONS ===
        # Add a small bias based on template index to prevent always selecting the same templates
        # This ensures that templates with identical scores don't always resolve to the same one
        diversity_factor = (template_idx % 100) / 10000  # Small factor based on index
        
        # If we have nothing to score on, return a small random value to enable selection
        if total_weight == 0:
            return random.uniform(0.01, 0.1) * random_factor
        
        # Calculate final score with randomization and diversity factors
        normalized_score = (score / total_weight) * random_factor + diversity_factor
        
        # Ensure score is between 0 and 1
        return max(0, min(normalized_score, 1.0))

    def validate(self, input_data: Union[str, Dict]) -> Dict:
        """Main validation workflow for handling malformed JSON inputs"""
        try:
            # Extract text for keyword analysis
            input_text = self._extract_text_from_input(input_data)
            logger.info(f"Extracted text for analysis: '{input_text[:100]}...'")
            
            # Extract features from text
            room_counts, object_counts, numeric_values = self._extract_keywords_and_counts(input_text)
            
            logger.info(f"Extracted room counts: {room_counts}")
            logger.info(f"Extracted object counts: {object_counts}")
            logger.info(f"Extracted numeric values: {numeric_values}")
            
            # Score all templates
            scores = []
            for i in range(len(self.templates)):
                score = self._score_template(i, room_counts, object_counts, numeric_values)
                scores.append((i, score))
            
            # Sort by score descending
            scores.sort(key=lambda x: x[1], reverse=True)
            
            # Get top 5 templates
            top_templates = scores[:5]
            logger.info(f"Top 5 template scores: {[(idx, round(score, 3)) for idx, score in top_templates]}")
            
            # If we have reasonable matches, randomly select one with weights proportional to scores
            if top_templates[0][1] > 0.2:  # Threshold can be adjusted
                # Extract indices and scores
                indices = [idx for idx, _ in top_templates]
                template_scores = [score for _, score in top_templates]
                
                # Use scores as weights, normalize to sum to 1
                weights = np.array(template_scores)
                weights = weights / weights.sum()
                
                # Randomly select template index based on weights
                selected_idx = np.random.choice(indices, p=weights)
                selected_score = dict(top_templates)[selected_idx]
                
                logger.info(f"Selected template {selected_idx} with score {selected_score:.3f}")
                return self.templates[selected_idx]
            else:
                # If no good matches, select a random template from the top 20
                top_20_indices = [idx for idx, _ in scores[:20]]
                selected_idx = random.choice(top_20_indices)
                logger.info(f"No strong matches found. Randomly selected template {selected_idx}")
                return self.templates[selected_idx]
                
        except Exception as e:
            logger.error(f"Error during validation: {str(e)}")
            # If all else fails, select a completely random template
            random_idx = random.randint(0, len(self.templates) - 1)
            logger.info(f"Error occurred. Using random template {random_idx}")
            return self.templates[random_idx]

    def _extract_text_from_input(self, input_data: Union[str, Dict]) -> str:
        """Extract usable text from malformed input"""
        if isinstance(input_data, dict):
            # If it's already a dict, convert to string for keyword extraction
            return json.dumps(input_data)
        
        # Remove JSON syntax characters to make plain text easier to analyze
        text = re.sub(r'[{}\[\]]', ' ', input_data)
        
        # Replace colons and commas with spaces
        text = re.sub(r'[,:]', ' ', text)
        
        # Remove extra quotes
        text = re.sub(r'[\'"]', '', text)
        
        # Replace multiple spaces with a single space
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def save_output(self, data: Dict, filename: str = "output.json"):
        """Save validated JSON to file"""
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved validated JSON to {filename}")

if __name__ == "__main__":
    # Example usage
    validator = ProcTHORValidator(template_file="procthor_10k.jsonl")

    # Example input (replace with your actual input)
    test_input = '''{"id": "house_2448", "numRooms": 2, "floors": 2, "dimensions": "x": 16, "y": 16, "rooms": ["roomType": "kitchen", "name": "kitchen", "floorLevel": 0, "objects": ["objectType": "sink", "assetId": "sink", "position": "x": 1.23, "y": 0, "z": 1.91, "objectType": "table", "assetId": "table", "position": "x": 1.87, "y": 0, "z": 1.91, "objectType": "oven", "assetId": "oven", "position": "x": 1.87, "y": 0, "z": 1.91], "roomType": "living room", "name": "living room", "floorLevel": 0, "objects": ["objectType": "coffee table", "assetId": "coffee table", "position": "x": 1.87, "y": 0, "z": 1.91, "objectType": "sofa", "assetId": "sofa", "position": "x": 1.87, "y": 0, "z": 1.91, "objectType": "end table", "assetId": "end table", "position": "x": 1.87, "y": 0, "z": 1.91], "roomType": "bathroom", "name": "bathroom", "floorLevel": 0, "objects": ["objectType": "toilet", "assetId": "toilet", "position": "x": 1.87, "y": 0, "z": 1.91, "objectType": "shower", "assetId": "shower",}'''
    
    result = validator.validate(test_input)
    validator.save_output(result)