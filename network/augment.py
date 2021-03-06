from collections import namedtuple
from typing import Iterable, Tuple, NewType, Dict, List
import os
import json

import matplotlib.pyplot as plt
import matplotlib.patches as pat
from skimage import transform
from skimage.io import imread
import numpy as np


# entirely for collaboration purposes
Bbox = namedtuple('Bbox', 'i1 j1 i2 j2')
Img  =   NewType('Img', np.array)

# the final form of our training data
# Imgs:   4D tensor, a batch of images of fixed size
Imgs =   NewType('Imgs', np.array)    # shape = (bs, w, h, 3)

# Labels: 4D tensor, a batch of labels if fixed size
#
# - labels[l][i][j][0, 1] \in (0, 1) represent the width & height of the
#   (potential) bounding box of center (i, j), in the image's system
#   of coordinates
#
# - labels[l][i][j][2] \in (0, 1) represents the probability that the
#   bounding box (above) is indeed valid
#
# during training, we fix the dimensions of the labels to equal the
# dimensions of the output of the network for fixed size images
Labels = NewType('Labels', np.array)  # shape = (bs, Si, Sj, 3)


def rotate_label(label, rot_matrix):
	v1, v2 = np.zeros((3, 1)), np.zeros((3, 1))
	v1[:2, 0] = label[:2]
	v2[:2, 0] = label[2:]

	new1 = rot_matrix @ v1
	new2 = rot_matrix @ v2

	new_label = (new1[0, 0], new1[1, 0], new2[0, 0], new2[1, 0])
	return new_label

# We rotate with random angle of rotation
# Rotate image by a certain angle around its center.
# Returns the rotated image along with the new labels 
def rotate(img_copy, labels):
    rotation = transform.SimilarityTransform(
		scale=1, rotation=np.random.uniform(0, 2 * np.pi)) # educated choice
    image_rotated = transform.warp(img_copy, rotation)
    rot_matrix = rotation.params 

    new_labels = []
    for label in labels: 
        new_labels.append(rotate_label(label, rot_matrix))

    return image_rotated, new_labels

def flip_label(label, axis, rows, cols):
    if axis == 0: 
        i1 = rows - label.i2
        i2 = rows - label.i1

        j1 = label.j1
        j2 = label.j2
    else: 
        j1 = cols - label.j2
        j2 = cols - label.j1

        i1 = label.i1
        i2 = label.i2

    new_label = (i1, j1, i2, j2)
    return new_label

"""
No skimage method designed to flip. Use numpy.flip(m, axis=None)
m : input array
axis = 0 : flip an array vertically
axis = 1 : flip an array horizontally
"""
# we flip and return the flipped image along with new labels 
def flip(img, labels):
    axis = np.random.choice([True, False], 1)
    new_img = np.flip(img, axis)

    new_labels = []
    for label in labels: 
        new_labels.append(flip_label(label, axis, img.shape[0], image.shape[1]))

    return new_img, new_labels

def _datagen(imgs: Dict[str, Img],
	labels: Dict[str, List[Bbox]], Si: int, Sj: int, bs: int) ->\
	Iterable[Tuple[Imgs, Labels]]:
	'''@brief generator for infinite data augmentation

	@param imgs the complete image dataset
	@param labels the complete labels dataset
	@param Si number of rows of label tensor
	@param Sj number of cols of label tensor
	@param bs minibatch size

	@returns a generator for infinite data augmentation
	'''

	def _():  # individually augment images
		ids = list(imgs.keys())
		while True:
			# select image
			idd = ids[np.random.randint(len(ids))]
			im = imgs[idd]
			lbls = labels[idd]

			# ditch non-labeled image
			if not len(lbls):
				continue

			# rotate and possibly flip
			rotim, rotlbls = im, lbls  # rotate(im, lbls)
			# sflip = np.random.randint(1)
			# if sflip:
			# 	rotim, rotlbls = flip(rotim, rotlbls)

			# build label tensor
			# fig, ax = plt.subplots(1)
			# ax.imshow(rotim)

			lb = np.zeros((Si, Sj, 3))
			for i1, j1, i2, j2 in rotlbls:
				a = int((Si / rotim.shape[0]) * (i1 + i2) / 2)
				b = int((Sj / rotim.shape[1]) * (j1 + j2) / 2)
				lb[a, b, 0] = (i2 - i1) / rotim.shape[0]
				lb[a, b, 1] = (j2 - j1) / rotim.shape[1]
				lb[a, b, 2] = 1

				# r = pat.Rectangle((j1, i1), j2 - j1, i2 - i1, fill=False)
				# ax.add_patch(r)

			plt.show()

			yield rotim, lb

	# aggregation into minibatches
	mli, mlb = [], []
	for sim, slb in _():
		mli.append(sim)
		mlb.append(slb)
		if(len(mli) == bs):
			yield np.stack(mli), np.stack(mlb)
			mli.clear()
			mlb.clear()

def datagen(imgsp, lblsp, Si, Sj, bs):
	ims = dict()
	for p, ds, fs in os.walk(imgsp):
		for fname in fs:
			if not fname.endswith('.JPG'):
				continue
			ims[fname[:-4]] = imread(os.path.join(p, fname))

	with open(lblsp) as fl:
		lbls = json.load(fl)

	return _datagen(ims, lbls, Si, Sj, bs)


if __name__ == '__main__':
	gen = datagen('downscaled1000x750', 'labels1000x750.json', 100, 75, 10)
	for mbi, mbl in gen:
		print(mbi.shape, mbl.shape)
