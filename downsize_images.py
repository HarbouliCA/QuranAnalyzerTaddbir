"""
Image Downsizing Script
Compresses JPG images to reduce file size while maintaining quality.
"""

import os
from PIL import Image
from pathlib import Path


def downsize_images(
    input_dir,
    output_dir=None,
    max_size=(1920, 1080),
    quality=85,
    optimize=True,
    backup=False
):
    """
    Downsize JPG images in a directory.
    
    Args:
        input_dir: Path to directory containing images
        output_dir: Path to output directory (None = overwrite originals)
        max_size: Maximum dimensions (width, height) - images will be scaled proportionally
        quality: JPG quality (1-100, default 85)
        optimize: Enable JPG optimization (default True)
        backup: Create .bak backup files before overwriting (default False)
    """
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"Error: Directory '{input_dir}' does not exist!")
        return
    
    # Setup output directory
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = input_path
    
    # Find all JPG files
    jpg_patterns = ['*.jpg', '*.jpeg', '*.JPG', '*.JPEG']
    jpg_files = []
    for pattern in jpg_patterns:
        jpg_files.extend(input_path.glob(pattern))
    
    if not jpg_files:
        print(f"No JPG files found in '{input_dir}'")
        return
    
    print(f"Found {len(jpg_files)} JPG images")
    print(f"Settings: max_size={max_size}, quality={quality}, optimize={optimize}")
    print("-" * 60)
    
    total_original_size = 0
    total_new_size = 0
    processed_count = 0
    
    for img_path in jpg_files:
        try:
            # Get original file size
            original_size = img_path.stat().st_size
            total_original_size += original_size
            
            # Open and process image
            with Image.open(img_path) as img:
                # Convert RGBA to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = rgb_img
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if needed
                original_dimensions = img.size
                if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    resized = True
                else:
                    resized = False
                
                # Prepare output path
                if output_dir:
                    out_path = output_path / img_path.name
                else:
                    out_path = img_path
                    # Create backup if requested
                    if backup and not resized:  # Only backup if overwriting
                        backup_path = img_path.with_suffix(img_path.suffix + '.bak')
                        img_path.rename(backup_path)
                
                # Save optimized image
                img.save(
                    out_path,
                    'JPEG',
                    quality=quality,
                    optimize=optimize
                )
            
            # Get new file size
            new_size = out_path.stat().st_size
            total_new_size += new_size
            
            # Calculate savings
            saved = original_size - new_size
            saved_percent = (saved / original_size * 100) if original_size > 0 else 0
            
            # Print results
            resize_info = f" (resized from {original_dimensions})" if resized else ""
            print(f"✓ {img_path.name}: {original_size/1024:.1f}KB → {new_size/1024:.1f}KB "
                  f"(-{saved_percent:.1f}%){resize_info}")
            
            processed_count += 1
            
        except Exception as e:
            print(f"✗ Error processing {img_path.name}: {str(e)}")
    
    # Print summary
    print("-" * 60)
    print(f"\nProcessed {processed_count}/{len(jpg_files)} images")
    print(f"Total size: {total_original_size/1024/1024:.2f}MB → {total_new_size/1024/1024:.2f}MB")
    
    if total_original_size > 0:
        total_saved = total_original_size - total_new_size
        total_saved_percent = (total_saved / total_original_size * 100)
        print(f"Total saved: {total_saved/1024/1024:.2f}MB ({total_saved_percent:.1f}%)")


if __name__ == "__main__":
    # Configuration
    IMAGE_DIR = r"C:\Users\alabe\OneDrive\Escritorio\images"
    
    # Option 1: Overwrite originals (default)
    downsize_images(
        input_dir=IMAGE_DIR,
        output_dir=None,  # Set to a path like IMAGE_DIR + "_compressed" to save separately
        max_size=(1920, 1080),  # Maximum dimensions
        quality=85,  # JPG quality (1-100, 85 is good balance)
        optimize=True,  # Enable optimization
        backup=False  # Set True to create .bak files before overwriting
    )
    
    # Option 2: Save to separate directory (uncomment to use)
    # downsize_images(
    #     input_dir=IMAGE_DIR,
    #     output_dir=IMAGE_DIR + "_compressed",
    #     max_size=(1920, 1080),
    #     quality=85,
    #     optimize=True
    # )
