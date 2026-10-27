from skimage import io, filters, morphology, measure, util
import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from pathlib import Path

#all variables for quick access fine tuning and maybe later adding into UI for changing
BACK_GRND_RADIUS = 12 # disk size for tophat
SIGMAS = [1,3]   # for edge detection filter
RIDGE_K = 8           # multiplier constant for ridge mask tuning
BRIGHTNESS_K = 8    # multiplier constant for brightness mask tuning
SML_OBJ_PIX = 15      # for removing small objects (size of smalles object)
MIN_CELL_SIZE = 200
CLOSING_RADIUS = 5
STRICT_K = 35
#decided to use MAD (median absolute deviation) because the very bright pixels bring up the mean and drown
#out fainter bundle pixels
def _mad(values, med):
    return np.median(np.abs(values-med)) * 1.4826    #standard MAD scaling value to sdev

def _preprocess(img):
    #converting images to usable format
    img = util.img_as_float(img)
    
    img = filters.gaussian(img, sigma=1)
    return img


def get_cell_area_pix(img):   #for finding num of pixels in the cytoplasm area
    
    img = util.img_as_float(img)
    gausX_img = filters.gaussian(img, sigma=4)      #effectively a copy of the cell mask area until the pixel counting but with just a higher gausian blur

    cell_msk = gausX_img > filters.threshold_li(img)
    cell_msk = morphology.remove_small_objects(cell_msk, max_size=MIN_CELL_SIZE)

    cell_msk = morphology.closing(cell_msk, morphology.disk(CLOSING_RADIUS))

    cell_area = np.count_nonzero(cell_msk)

    return cell_area

def get_cell_mask(img):     #creates a mask of full cell area
    if img.ndim == 3:
            img.color.rgb2gray(img[..., :3])
    img = util.img_as_float(img)
    gausX_img = filters.gaussian(img, sigma=4)      
    
    cell_msk = gausX_img > filters.threshold_li(img)
    cell_msk = morphology.remove_small_objects(cell_msk, max_size=MIN_CELL_SIZE)
    
    cell_msk = morphology.closing(cell_msk, morphology.disk(CLOSING_RADIUS))
    return cell_msk

def clean(img):     

    img = _preprocess(img)

    cell_mask = get_cell_mask(img)
    #definig footprint with decomp to speed it up
    footprint = morphology.disk(BACK_GRND_RADIUS, decomposition= 'sequence')
    #background subtraction
    tophat = morphology.white_tophat(img, footprint)

    #background detection
    ridges = filters.sato(tophat, sigmas=SIGMAS, black_ridges=False)

    #implementing cell mask into cleaning function
    top_cel_msk = tophat[cell_mask]
    top_med = np.median(top_cel_msk)
    top_mad = _mad(top_cel_msk, top_med)

    rid_cel_msk = ridges[cell_mask]
    rid_med = np.median(rid_cel_msk)
    rid_mad = _mad(rid_cel_msk, rid_med)

    #formula for following masks
    #Threshold = mean + (stdev * k)   (k is the Z score, or number of stdevs away from the mean)

    rid_thresh = rid_med + (RIDGE_K * rid_mad)
    rid_mask = ridges > rid_thresh

    bright_thresh = top_med + (BRIGHTNESS_K * top_mad)
    bright_mask = tophat > bright_thresh

    #overlaps all three masks and only outputs the overlap
    binary_image = rid_mask & bright_mask & cell_mask

    strict_cutoff = top_med + (STRICT_K * top_mad)
    labled = measure.label(binary_image)
    labled2 = measure.regionprops(labled, intensity_image=tophat)

    keep = [obj.label for obj in labled2 if obj.intensity_max > strict_cutoff]
    binary_image = np.isin(labled, keep)

    binary_image = morphology.remove_small_objects(binary_image, max_size=SML_OBJ_PIX)

    return binary_image

def get_bundle_area(img):
    bundl_msk = clean(img)
    bundl_area = np.count_nonzero(bundl_msk)
    return bundl_area

def get_bundl_dens(img, cleaned):
    bundl_msk = cleaned
    bundl_area = np.count_nonzero(bundl_msk)
    bundl_dens = bundl_area/(get_cell_area_pix(img))
    return bundl_dens

spur_length = 5

def bundle_count(bundle_mask):
    skel = morphology.skeletonize(bundle_mask)

    pruned = skel.copy()  #creats a usable copy of skel
    kernel = np.ones((3, 3), int)   #small kernel array for checking nearby pixels
    #spur remover
    for _ in range(spur_length):    
        adjacents = ndi.convolve(pruned.astype(int), kernel, mode='constant') * pruned   #runs the kernel over every pixel in the skeleton and deletes non skeleton pixels
        pruned[adjacents == 2] = False     #if there is only 2 its an endpoint 
    #rerunning it on the spurrless image to find true endpoints
    neighbors = ndi.convolve(pruned.astype(int), kernel, mode='constant') * pruned
    n_endpoints = np.count_nonzero(neighbors == 2)
    count_est = n_endpoints / 2

    return count_est

MIN_WHOLE_CELL = 20000
EDGE_FRACTION = 0.1
def count_per_cel(img, bundle_mask):
    mask = get_cell_mask(img)
    mask = morphology.remove_small_objects(mask, max_size=MIN_WHOLE_CELL)
    labels = measure.label(mask)

    edge = np.zeros(labels.shape, bool) #A check to see if the cell is touching any of the edge pixels
    edge[0, :] = True
    edge[-1, :] = True
    edge[:, 0] = True
    edge[:, -1] = True

    keep = []    # does not keep if a large majority of a cell is on the border meaning an edge cell with most of its area cut off
    for obj in measure.regionprops(labels):
        edge_px = np.count_nonzero((labels == obj.label) & edge)
        edge_fraction = edge_px / obj.perimeter
        if edge_fraction <= EDGE_FRACTION:
            keep.append(obj.label)
    num_cel = len(keep) 
    kept_cel = np.isin(labels, keep)
    bundl_in_cel = bundle_mask & kept_cel
    cnt_in_cell = bundle_count(bundl_in_cel)

    return cnt_in_cell / num_cel



def analyze_folder(folder, progress=None):    #creating the pandas df and exporting it as a csv
    #added a progress bar for QOL
    rows = []
    all_paths = sorted(Path(folder).rglob("*.png"))

    #MAC makes weird files that arent the images i want so this excludes them
    img_paths = [p for p in all_paths if not ("__MACOSX" in p.parts or p.name.startswith("._"))]

    for i, path in enumerate(img_paths):
        try:
            img = io.imread(str(path), as_gray= True)
            cleaned = clean(img)
            count_est = count_per_cel(img, cleaned)
            bndl_pix = np.count_nonzero(cleaned)
            cel_pix = get_cell_area_pix(img)
            row = {
                "file" : path.name,
                "condition" : path.parent.name,
                "count_est": count_est,
                "density" : bndl_pix / cel_pix,
                "error" : ""
            }
        except Exception as E:
            row = {"file": path.name, "condition": path.parent.name, "error": str(E)}

        rows.append(row)
        print(f"done: {path.name}")
        if progress is not None:
            progress(i+1, len(img_paths))

    df = pd.DataFrame(rows)
    df["flagged"] = False
    df["note"] = ""
    return df