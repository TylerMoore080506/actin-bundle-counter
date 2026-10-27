# actin-bundle-counter
A small web app/tool for automatic quanitification of fiber like cell structures in microscopy images. Upload a zip of images sorted into one folder per condition. Images tested take 5-10 seconds per images but this can vary depending on device. Once finished it will export a downloadable csv with the condition, bundle pixel density and and a rough bundle count for every image. 

Made using Python, with libraries scikit-image and Streamlit

---

## Data It Measures
for each image the app exports

| Column | Meaning |
|---|---|
| `file` | file name |
| `condition` | Name of the folder |
| `density` | Bundle area / cell area, as a fraction |
| `count_est` | Estimated number of bundles per cell (see (#limitations)) |
| `error` | Empty if no issues; otherwise prints the error message |
| `flagged`, `note` |A blank column for marking afterwards|

--- 

## Installation

Requires Python 3.10 or newer

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
python -m pip install -r requirements.txt
```

`requirements.txt`:

```
streamlit
numpy
pandas
scikit-image>=0.26
scipy
```

---

## How it works

1. **Preprocessing:** the image is converted to a float and lightly smoothed (Gaussian, sigma = 1).
2. **Cell mask:** a heavier blur (σ = 4) is applied then ran through a Li threshold to create a cell area mask
3. **Background subtraction:** a white top-hat filter (disk, radius 12 px) removes noise and keeps only the bright fiber structures
4. **Ridge detection:** a Sato edge filter highlights thin, line-shaped structures.
5. **Thresholding:** a pixel is kept as a bundle pixel if it is both more ridge-like and brighter than typical for its own cell. "Typical" is the median, and the spread is the median absolute deviation (MAD), both were measured inside only the cell mask so outliers dont disrupt the cutoff
6. **Object filter:** each object is kept only if its brightest point is well above typical removing textures and specs
7. **Density:** bundle pixels / cell pixels.
8. **Count:** the bundle mask is skeletonized, short spurs are removed, and endpoints are counted. Every bundle has 2 ends so bundle count ≈ endpoints / 2.
9. **Per-cell count:** cells that are mostly off the image edge or too small to be whole cells, are excluded, and the count is divided by the number of remaining cells.

### Parameters

All tuning values are constants at the top of `analysis.py`:
if you want you can tweak these to get different results but these are best from my images tested

| Constant | Value | Purpose |
|---|---|---|
| `BACK_GRND_RADIUS` | 12 | Top-hat disk radius (px) |
| `SIGMAS` | [1, 3] | Scales for the ridge filter |
| `RIDGE_K` | 8 | Ridge threshold, in MADs above the median |
| `BRIGHTNESS_K` | 8 | Brightness threshold, in MADs above the median |
| `STRICT_K` | 35 | Minimum peak brightness for an object to be kept |
| `SML_OBJ_PIX` | 15 | Smallest bundle object kept (px) |
| `MIN_CELL_SIZE` | 200 | Smallest region kept in the cell mask (px) |
| `CLOSING_RADIUS` | 5 | Gap-closing radius for the cell mask (px) |
| `MIN_WHOLE_CELL` | 20000 | Smallest region counted as a cell (px) |
| `EDGE_FRACTION` | 0.1 | Cells with more than this fraction of their outline on the image border are excluded from the per-cell count |
| `spur_length` | 5 | Skeleton spur length pruned before counting (px) |

IMPORTANT:
The pixel-based values were tuned on 2048 × 2048 images at one magnification. Images at a different resolution or magnification will likely need them adjusted.

---

## Limitations

- **The count is an estimate, not a manual-equivalent count.** If your cell has a high density of actin bundles it will miscount them because with this type or program its not possible to differentiate overlapping bundles to an extent, lower density samples are a higher accuracy.
- **Touching cells are counted as one cell.** I didn't have access to a dapi stained channel for these images so thresholding was used to find cell count and on overlapped cells its sometimes impossible to tell so that will add some error. 
- **Very faint, fine filament meshes may be missed.** Detection is tuned toward bright, distinct bundles, some tiny very faint bundles were missed in some images but this was rare and generally most of the bundles were caught.
- **Density is the more robust measure** of the two. It doesn't depend on separating individual bundles and calculates just on pixel counts which error only comes from possible 3D orientations of the cells causing a smaller cell area than reality but that is minor. 

Always review a sample of images by eye. The `flagged` and `note` columns are there for that.

---

## Privacy

When run locally, images never leave your computer. Uploads are extracted to a temporary folder that is deleted after each run, and no images or results are stored by the app.

This repository contains code only. No image data is included.

---

## Project structure

```
├── analysis.py        # image analysis functions and parameters
├── app.py             # Streamlit web interface
├── requirements.txt   # Python dependencies
└── README.md
```

---

## Author

Tyler Moore, East Carolina University

## License

MIT License LICENSE