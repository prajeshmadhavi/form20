#!/usr/bin/env python3
"""
OCR Extractor for Form 20 PDFs
Handles scanned, rotated, and low-quality PDFs with advanced preprocessing
"""

import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

# Image processing imports
try:
    import cv2
    from PIL import Image
    import pytesseract
    from pdf2image import convert_from_path
    import fitz  # PyMuPDF
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install opencv-python pillow pytesseract pdf2image PyMuPDF")
    exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRExtractor:
    """Advanced OCR extraction for Form 20 PDFs"""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="form20_ocr_")
        self.tesseract_config = self.get_tesseract_config()
        self.preprocessing_params = self.get_preprocessing_params()

    def get_tesseract_config(self) -> str:
        """Get optimal Tesseract configuration for Form 20"""
        return "--psm 6 --oem 3 -c tessedit_char_whitelist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .,()-/'"

    def get_preprocessing_params(self) -> Dict:
        """Get image preprocessing parameters"""
        return {
            "dpi": 300,  # Resolution for PDF to image conversion
            "rotation_threshold": 0.5,  # Minimum confidence for rotation detection
            "denoise_strength": 7,  # Denoising filter strength
            "sharpen_kernel_size": 3,  # Sharpening kernel size
            "adaptive_threshold_block_size": 11,  # For binarization
            "adaptive_threshold_c": 2,  # Constant for adaptive threshold
            "deskew_angle_limit": 5,  # Maximum deskew angle in degrees
            "min_text_area": 100,  # Minimum area for text regions
            "table_detection_threshold": 0.7  # Confidence for table detection
        }

    def extract(self, pdf_path: Path) -> Dict:
        """Main extraction method for OCR-based processing"""
        logger.info(f"Starting OCR extraction for {pdf_path}")

        try:
            # Step 1: Convert PDF to images
            images = self.pdf_to_images(pdf_path)
            logger.info(f"Converted PDF to {len(images)} images")

            # Step 2: Preprocess each image
            processed_images = []
            for i, img in enumerate(images):
                processed = self.preprocess_image(img, page_num=i+1)
                processed_images.append(processed)

            # Step 3: Detect and extract tables
            extracted_data = []
            for i, img in enumerate(processed_images):
                # Try multiple OCR strategies
                page_data = self.extract_with_multiple_strategies(img, page_num=i+1)
                extracted_data.append(page_data)

            # Step 4: Parse and structure the data
            structured_data = self.parse_form20_data(extracted_data)

            # Step 5: Validate and calculate confidence
            validation_result = self.validate_ocr_results(structured_data)

            return {
                "status": "success",
                "method": "OCR",
                "pages_processed": len(images),
                "records": structured_data.get("records", []),
                "record_count": len(structured_data.get("records", [])),
                "summary": structured_data.get("summary", {}),
                "confidence_score": validation_result["confidence"],
                "quality_score": validation_result["quality_score"],
                "warnings": validation_result.get("warnings", []),
                "metadata": {
                    "pdf_path": str(pdf_path),
                    "extraction_method": "OCR with preprocessing",
                    "preprocessing_applied": True
                }
            }

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "method": "OCR"
            }
        finally:
            # Cleanup temp files
            self.cleanup_temp_files()

    def pdf_to_images(self, pdf_path: Path) -> List[np.ndarray]:
        """Convert PDF pages to images for OCR processing"""
        images = []

        # Try pdf2image first (better quality)
        try:
            pil_images = convert_from_path(
                pdf_path,
                dpi=self.preprocessing_params["dpi"],
                output_folder=self.temp_dir
            )

            for pil_img in pil_images:
                # Convert PIL to OpenCV format
                img_array = np.array(pil_img)
                if len(img_array.shape) == 3:
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                images.append(img_array)

        except Exception as e:
            logger.warning(f"pdf2image failed, trying PyMuPDF: {e}")

            # Fallback to PyMuPDF
            doc = fitz.open(str(pdf_path))
            for page_num in range(len(doc)):
                page = doc[page_num]
                mat = fitz.Matrix(self.preprocessing_params["dpi"]/72,
                                 self.preprocessing_params["dpi"]/72)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")

                # Convert to numpy array
                nparr = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                images.append(img)

            doc.close()

        return images

    def preprocess_image(self, image: np.ndarray, page_num: int) -> np.ndarray:
        """Apply comprehensive preprocessing to improve OCR accuracy"""
        logger.info(f"Preprocessing page {page_num}")

        # Step 1: Detect and correct rotation
        rotated = self.correct_rotation(image)

        # Step 2: Deskew
        deskewed = self.deskew_image(rotated)

        # Step 3: Remove noise
        denoised = self.remove_noise(deskewed)

        # Step 4: Enhance contrast
        enhanced = self.enhance_contrast(denoised)

        # Step 5: Sharpen text
        sharpened = self.sharpen_image(enhanced)

        # Step 6: Binarization (convert to black and white)
        binary = self.binarize_image(sharpened)

        # Step 7: Remove borders and lines (optional for forms)
        cleaned = self.remove_lines(binary)

        # Save preprocessed image for debugging
        debug_path = Path(self.temp_dir) / f"preprocessed_page_{page_num}.png"
        cv2.imwrite(str(debug_path), cleaned)
        logger.debug(f"Saved preprocessed image: {debug_path}")

        return cleaned

    def correct_rotation(self, image: np.ndarray) -> np.ndarray:
        """Detect and correct image rotation"""
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()

            # Use Hough Line Transform to detect predominant angles
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi/180, 200)

            if lines is not None:
                angles = []
                for rho, theta in lines[:, 0]:
                    angle = (theta * 180 / np.pi) - 90
                    if abs(angle) < 45:  # Only consider reasonable rotations
                        angles.append(angle)

                if angles:
                    # Get median angle
                    median_angle = np.median(angles)

                    if abs(median_angle) > 0.5:  # Only rotate if significant
                        logger.info(f"Rotating image by {median_angle:.2f} degrees")

                        # Get rotation matrix
                        (h, w) = image.shape[:2]
                        center = (w // 2, h // 2)
                        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)

                        # Perform rotation
                        rotated = cv2.warpAffine(
                            image, M, (w, h),
                            flags=cv2.INTER_CUBIC,
                            borderMode=cv2.BORDER_REPLICATE
                        )
                        return rotated

        except Exception as e:
            logger.warning(f"Rotation correction failed: {e}")

        return image

    def deskew_image(self, image: np.ndarray) -> np.ndarray:
        """Correct skew in scanned images"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

            # Find all contours
            coords = np.column_stack(np.where(gray > 0))

            if len(coords) > 100:  # Need enough points
                # Get minimum area rectangle
                angle = cv2.minAreaRect(coords)[-1]

                if angle < -45:
                    angle = 90 + angle

                if abs(angle) > self.preprocessing_params["deskew_angle_limit"]:
                    angle = 0  # Don't over-correct

                if abs(angle) > 0.1:
                    logger.info(f"Deskewing by {angle:.2f} degrees")
                    (h, w) = image.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    deskewed = cv2.warpAffine(
                        image, M, (w, h),
                        flags=cv2.INTER_CUBIC,
                        borderMode=cv2.BORDER_REPLICATE
                    )
                    return deskewed

        except Exception as e:
            logger.warning(f"Deskew failed: {e}")

        return image

    def remove_noise(self, image: np.ndarray) -> np.ndarray:
        """Remove noise from image"""
        # Apply bilateral filter to reduce noise while keeping edges sharp
        denoised = cv2.bilateralFilter(
            image,
            self.preprocessing_params["denoise_strength"],
            75, 75
        )

        # Additional morphological operations to remove small noise
        kernel = np.ones((2,2), np.uint8)
        denoised = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel)

        return denoised

    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance image contrast using CLAHE"""
        if len(image.shape) == 3:
            # Convert to LAB color space
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)

            # Apply CLAHE to lightness channel
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            l = clahe.apply(l)

            # Merge and convert back
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        else:
            # Grayscale
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced = clahe.apply(image)

        return enhanced

    def sharpen_image(self, image: np.ndarray) -> np.ndarray:
        """Sharpen image to improve text clarity"""
        # Create sharpening kernel
        kernel = np.array([
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0]
        ])

        sharpened = cv2.filter2D(image, -1, kernel)
        return sharpened

    def binarize_image(self, image: np.ndarray) -> np.ndarray:
        """Convert to binary image using adaptive thresholding"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Apply adaptive threshold
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            self.preprocessing_params["adaptive_threshold_block_size"],
            self.preprocessing_params["adaptive_threshold_c"]
        )

        return binary

    def remove_lines(self, image: np.ndarray) -> np.ndarray:
        """Remove horizontal and vertical lines from forms"""
        try:
            # Create kernels for line detection
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))

            # Detect lines
            horizontal_lines = cv2.morphologyEx(image, cv2.MORPH_OPEN, horizontal_kernel)
            vertical_lines = cv2.morphologyEx(image, cv2.MORPH_OPEN, vertical_kernel)

            # Remove lines
            image_no_lines = image.copy()
            image_no_lines[horizontal_lines == 255] = 255
            image_no_lines[vertical_lines == 255] = 255

            return image_no_lines

        except Exception as e:
            logger.warning(f"Line removal failed: {e}")
            return image

    def extract_with_multiple_strategies(self, image: np.ndarray, page_num: int) -> Dict:
        """Try multiple OCR strategies to maximize extraction success"""
        strategies = [
            ("tesseract_standard", self.tesseract_ocr),
            ("tesseract_with_psm", self.tesseract_table_ocr),
            ("contour_based", self.contour_based_ocr),
        ]

        best_result = None
        best_confidence = 0

        for strategy_name, strategy_func in strategies:
            try:
                logger.info(f"Trying {strategy_name} for page {page_num}")
                result = strategy_func(image)

                if result and result.get("confidence", 0) > best_confidence:
                    best_confidence = result["confidence"]
                    best_result = result
                    best_result["strategy"] = strategy_name

            except Exception as e:
                logger.warning(f"Strategy {strategy_name} failed: {e}")

        if not best_result:
            # Fallback to basic OCR
            text = pytesseract.image_to_string(image)
            best_result = {
                "text": text,
                "confidence": 0.5,
                "strategy": "fallback"
            }

        logger.info(f"Best strategy for page {page_num}: {best_result.get('strategy')} "
                   f"(confidence: {best_result.get('confidence', 0):.2f})")

        return best_result

    def tesseract_ocr(self, image: np.ndarray) -> Dict:
        """Standard Tesseract OCR"""
        # Get detailed OCR data
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        # Calculate average confidence
        confidences = [int(c) for c in data['conf'] if int(c) > 0]
        avg_confidence = np.mean(confidences) / 100 if confidences else 0

        # Reconstruct text with layout
        text_lines = []
        current_line = []
        last_top = 0

        for i in range(len(data['text'])):
            if int(data['conf'][i]) > 0:
                # Check if new line
                if abs(data['top'][i] - last_top) > 10 and current_line:
                    text_lines.append(' '.join(current_line))
                    current_line = []

                current_line.append(data['text'][i])
                last_top = data['top'][i]

        if current_line:
            text_lines.append(' '.join(current_line))

        return {
            "text": '\n'.join(text_lines),
            "confidence": avg_confidence,
            "data": data
        }

    def tesseract_table_ocr(self, image: np.ndarray) -> Dict:
        """Tesseract with table-specific PSM mode"""
        # PSM 6: Uniform block of text
        config = "--psm 6 --oem 3"

        text = pytesseract.image_to_string(image, config=config)

        # Try to detect table structure
        lines = text.strip().split('\n')
        table_data = []

        for line in lines:
            # Split by multiple spaces or tabs
            cells = re.split(r'\s{2,}|\t', line.strip())
            if cells and any(cells):
                table_data.append(cells)

        return {
            "text": text,
            "table_data": table_data,
            "confidence": 0.7 if table_data else 0.3
        }

    def contour_based_ocr(self, image: np.ndarray) -> Dict:
        """Extract text from detected contours (cells)"""
        # Find contours
        contours, _ = cv2.findContours(
            255 - image,  # Invert for text detection
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # Filter and sort contours
        valid_contours = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > self.preprocessing_params["min_text_area"]:
                x, y, w, h = cv2.boundingRect(cnt)
                valid_contours.append((y, x, w, h, cnt))

        # Sort by position (top to bottom, left to right)
        valid_contours.sort(key=lambda c: (c[0], c[1]))

        # Extract text from each contour
        extracted_texts = []
        total_confidence = 0

        for y, x, w, h, cnt in valid_contours:
            # Extract ROI
            roi = image[y:y+h, x:x+w]

            # Apply OCR to ROI
            text = pytesseract.image_to_string(roi, config=self.tesseract_config)

            if text.strip():
                extracted_texts.append({
                    "text": text.strip(),
                    "bbox": (x, y, w, h)
                })

        return {
            "text": '\n'.join([t["text"] for t in extracted_texts]),
            "regions": extracted_texts,
            "confidence": 0.6 if extracted_texts else 0.2
        }

    def parse_form20_data(self, extracted_data: List[Dict]) -> Dict:
        """Parse OCR output to extract Form 20 specific fields"""
        all_text = '\n'.join([page.get("text", "") for page in extracted_data])

        # Initialize result structure
        result = {
            "records": [],
            "summary": {},
            "metadata": {}
        }

        # Extract constituency number
        const_pattern = r'AC[_\-\s]*(\d+)'
        const_match = re.search(const_pattern, all_text, re.IGNORECASE)
        if const_match:
            result["summary"]["constituency_number"] = f"AC_{const_match.group(1)}"

        # Extract total electors
        electors_pattern = r'Total.*Electors[\s:]*(\d+)'
        electors_match = re.search(electors_pattern, all_text, re.IGNORECASE)
        if electors_match:
            result["summary"]["total_electors"] = int(electors_match.group(1))

        # Extract candidate data and votes
        # Pattern for candidate rows
        candidate_pattern = r'(\d+)\s+([A-Za-z\s]+?)\s+([A-Za-z\s]+?)\s+(\d+)'

        for line in all_text.split('\n'):
            match = re.match(candidate_pattern, line)
            if match:
                record = {
                    "serial_no": match.group(1),
                    "candidate_name": match.group(2).strip(),
                    "party": match.group(3).strip(),
                    "votes": int(match.group(4))
                }
                result["records"].append(record)

        # Extract NOTA
        nota_pattern = r'NOTA[\s:]*(\d+)'
        nota_match = re.search(nota_pattern, all_text, re.IGNORECASE)
        if nota_match:
            result["summary"]["nota"] = int(nota_match.group(1))

        # Extract rejected votes
        rejected_pattern = r'Rejected.*Votes[\s:]*(\d+)'
        rejected_match = re.search(rejected_pattern, all_text, re.IGNORECASE)
        if rejected_match:
            result["summary"]["rejected_votes"] = int(rejected_match.group(1))

        # Extract total votes
        total_pattern = r'Total.*Valid.*Votes[\s:]*(\d+)'
        total_match = re.search(total_pattern, all_text, re.IGNORECASE)
        if total_match:
            result["summary"]["total_valid_votes"] = int(total_match.group(1))

        # Try to extract from table data if available
        for page in extracted_data:
            if "table_data" in page:
                self.parse_table_data(page["table_data"], result)

        return result

    def parse_table_data(self, table_data: List[List[str]], result: Dict):
        """Parse structured table data"""
        for row in table_data:
            # Skip header rows
            if not row or not row[0].isdigit():
                continue

            try:
                # Assuming format: [poll_no, candidate, party, votes, ...]
                if len(row) >= 4:
                    record = {
                        "polling_station": row[0],
                        "data": row[1:]
                    }

                    # Try to extract vote counts
                    for cell in row:
                        if cell.isdigit() and int(cell) > 0:
                            # Could be vote count
                            pass

                    result["records"].append(record)

            except Exception as e:
                logger.debug(f"Failed to parse row: {row}, error: {e}")

    def validate_ocr_results(self, data: Dict) -> Dict:
        """Validate OCR results and calculate confidence"""
        validation = {
            "is_valid": True,
            "confidence": 0.0,
            "quality_score": 0.0,
            "warnings": [],
            "errors": []
        }

        # Check if we have minimum required data
        if not data.get("records"):
            validation["warnings"].append("No records extracted")
            validation["confidence"] = 0.1
        else:
            # Calculate confidence based on data completeness
            record_count = len(data["records"])

            # Expected range for polling stations
            if record_count < 50:
                validation["warnings"].append(f"Low record count: {record_count}")
                validation["confidence"] = 0.5
            elif record_count > 500:
                validation["warnings"].append(f"High record count: {record_count}")
                validation["confidence"] = 0.7
            else:
                validation["confidence"] = 0.8

        # Check summary fields
        required_summary = ["constituency_number", "total_valid_votes", "nota"]
        summary_complete = sum(1 for field in required_summary
                             if field in data.get("summary", {}))

        validation["confidence"] *= (summary_complete / len(required_summary))

        # Calculate quality score
        validation["quality_score"] = min(validation["confidence"] * 1.2, 1.0)

        # Determine validity
        validation["is_valid"] = validation["confidence"] > 0.3

        return validation

    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.debug(f"Cleaned up temp directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {e}")


class OCRConfig:
    """Configuration management for OCR processing"""

    @staticmethod
    def get_config() -> Dict:
        """Get OCR configuration"""
        return {
            "engines": {
                "tesseract": {
                    "enabled": True,
                    "languages": ["eng", "mar"],  # English and Marathi
                    "psm_modes": [3, 6, 11],  # Different page segmentation modes
                    "oem_mode": 3  # OCR Engine Mode (LSTM)
                },
                "easyocr": {
                    "enabled": False,  # Optional alternative
                    "languages": ["en", "mr"]
                }
            },
            "preprocessing": {
                "enable_rotation_correction": True,
                "enable_deskew": True,
                "enable_noise_removal": True,
                "enable_contrast_enhancement": True,
                "enable_sharpening": True,
                "enable_line_removal": True
            },
            "quality_thresholds": {
                "min_confidence": 0.6,
                "min_text_length": 100,
                "max_error_rate": 0.2
            },
            "performance": {
                "max_pages": 50,  # Maximum pages to process
                "timeout_seconds": 300,  # 5 minutes timeout
                "parallel_pages": False  # Process pages in parallel
            }
        }


def main():
    """Test OCR extraction on a sample PDF"""
    import argparse

    parser = argparse.ArgumentParser(description="OCR Extractor for Form 20 PDFs")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--save-preprocessed", action="store_true",
                       help="Save preprocessed images")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    extractor = OCRExtractor()
    result = extractor.extract(Path(args.pdf_path))

    # Print results
    print("\n" + "="*60)
    print("OCR EXTRACTION RESULTS")
    print("="*60)
    print(f"Status: {result['status']}")

    if result['status'] == 'success':
        print(f"Method: {result['method']}")
        print(f"Pages Processed: {result['pages_processed']}")
        print(f"Records Extracted: {result['record_count']}")
        print(f"Confidence Score: {result['confidence_score']:.2f}")
        print(f"Quality Score: {result['quality_score']:.2f}")

        if result.get('warnings'):
            print("\nWarnings:")
            for warning in result['warnings']:
                print(f"  - {warning}")

        if result.get('summary'):
            print("\nSummary Data:")
            for key, value in result['summary'].items():
                print(f"  {key}: {value}")

        # Save results
        output_file = Path(args.pdf_path).stem + "_ocr_result.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nResults saved to: {output_file}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()