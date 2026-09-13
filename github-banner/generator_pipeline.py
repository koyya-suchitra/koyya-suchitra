import numpy as np
from PIL import Image, ImageOps, ImageFilter
import json

SRC = '/mnt/user-data/uploads/1789289852915_image.png'
GRID_W, GRID_H = 300, 340
CROP_BOX = (125, 0, 1066, 1129)  # head-and-shoulders crop, avoids laptop intrusion

def load_and_process():
    im = Image.open(SRC).convert('RGB')
    im = im.crop(CROP_BOX)
    im = im.resize((GRID_W, GRID_H), Image.LANCZOS)
    rgb = np.array(im, dtype=np.float64)

    # --- background segmentation ---
    # sample background color from the four corners of the crop (solid red wall)
    corners = np.array([rgb[0, 0], rgb[0, -1], rgb[-1, 0], rgb[-1, -1]])
    bg_color = corners.mean(axis=0)
    dist = np.sqrt(((rgb - bg_color) ** 2).sum(axis=2))
    fg_mask = dist > 40  # foreground = far enough from sampled background color

    # light morphological cleanup so the mask isn't speckled
    from scipy.ndimage import binary_closing, binary_opening, binary_fill_holes
    fg_mask = binary_closing(fg_mask, structure=np.ones((5, 5)))
    fg_mask = binary_opening(fg_mask, structure=np.ones((3, 3)))
    fg_mask = binary_fill_holes(fg_mask)

    gray = ImageOps.grayscale(im)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = gray.filter(ImageFilter.UnsharpMask(radius=3, percent=140, threshold=2))
    # gentle midtone lift: autocontrast's black-point stretch (driven by dark
    # hair) otherwise pulls skin tones down near the ink threshold and the
    # face fills in solid instead of reading as a stippled gradient
    gamma = 1.9
    lut = [int(255 * ((i / 255) ** (1 / gamma))) for i in range(256)]
    gray = gray.point(lut)
    return gray, fg_mask

def serpentine_floyd_steinberg(gray_img, fg_mask):
    """1-bit Floyd-Steinberg dithering, serpentine (boustrophedon) scan order.
    Dots = 'ink' = dark source pixels (hair, shadows, contours) -- these
    read as bright cyan/violet dot clusters against the dark banner
    background. Background pixels (outside fg_mask) never receive dots."""
    arr = np.array(gray_img, dtype=np.float64)
    h, w = arr.shape
    out = np.zeros((h, w), dtype=np.uint8)
    for y in range(h):
        if y % 2 == 0:
            xs = range(w)
        else:
            xs = range(w - 1, -1, -1)
        for x in xs:
            old = arr[y, x]
            new = 255.0 if old > 127.5 else 0.0
            out[y, x] = 1 if new == 0.0 else 0  # dark/ink pixel -> dot
            err = old - new
            # serpentine-aware neighbor offsets
            step = 1 if y % 2 == 0 else -1
            nxs = [(y, x + step), (y + 1, x - step), (y + 1, x), (y + 1, x + step)]
            weights = [7/16, 3/16, 5/16, 1/16]
            for (ny, nx), wgt in zip(nxs, weights):
                if 0 <= ny < h and 0 <= nx < w:
                    arr[ny, nx] += err * wgt
    out = out & fg_mask.astype(np.uint8)
    return out  # 1 = dot present, 0 = empty

def extract_dots(bitmap):
    ys, xs = np.nonzero(bitmap)
    return list(zip(xs.tolist(), ys.tolist()))

if __name__ == '__main__':
    gray, fg_mask = load_and_process()
    gray.save('/home/claude/stage_gray.png')
    Image.fromarray((fg_mask*255).astype(np.uint8)).save('/home/claude/stage_mask.png')
    bitmap = serpentine_floyd_steinberg(gray, fg_mask)
    dots = extract_dots(bitmap)
    print('grid', GRID_W, GRID_H, 'dots', len(dots), 'density', len(dots)/(GRID_W*GRID_H))
    with open('/home/claude/dots.json', 'w') as f:
        json.dump({'grid_w': GRID_W, 'grid_h': GRID_H, 'dots': dots}, f)
    # quick raster preview of the dot field
    prev = Image.new('RGB', (GRID_W, GRID_H), (10, 16, 31))
    px = prev.load()
    for (x, y) in dots:
        px[x, y] = (34, 211, 238)
    prev.resize((GRID_W*2, GRID_H*2), Image.NEAREST).save('/home/claude/preview_dots.png')
