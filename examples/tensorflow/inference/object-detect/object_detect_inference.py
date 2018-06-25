from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from PIL import Image
import numpy as np
import tensorflow as tf

from uai.arch.tf_model import TFAiUcloudModel
import os
import sys
import tensorflow as tf
from collections import defaultdict
from io import StringIO
import ops as utils_ops

class ObjectDetectModel(TFAiUcloudModel):
	"""
	Object detect model
	"""

	def __init__(self, conf):
		super(ObjectDetectModel, self).__init__(conf)

	def load_model(self):
	
	  
		IMAGE_SIZE = (12, 8)
		NUM_CLASSES = 37
	
		sess = tf.Session()

		with sess.as_default():
			# Load the model
			self._graph = tf.Graph()
			with self._graph.as_default():
				od_graph_def = tf.GraphDef()
				with tf.gfile.GFile(os.path.join(self.model_dir, "frozen_inference_graph.pb"), 'rb') as fid:
					serialized_graph = fid.read()
					od_graph_def.ParseFromString(serialized_graph)
					tf.import_graph_def(od_graph_def, name='')

			label_map = label_map_util.load_labelmap(os.path.join(self.model_dir, "graph.pbtxt"))
			categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
			category_index = label_map_util.create_category_index(categories)

		# Get input and output tensors
		images_placeholder = tf.get_default_graph().get_tensor_by_name("input:0")
		embeddings = tf.get_default_g raph().get_tensor_by_name("embeddings:0")
		phase_train_placeholder = tf.get_default_graph().get_tensor_by_name("phase_train:0")

		self._images_placeholder=images_placeholder
		self._embeddings=embeddings
		self._phase_train_placeholder=phase_train_placeholder
		self._sess = sess


	def load_image_into_numpy_array(self, image):
		(im_width, im_height) = image.size
		return np.array(image.getdata()).reshape(
					(im_height, im_width, 3)).astype(np.uint8)

					
					
	def execute(self, data, batch_size):
  
		IMAGE_SIZE = (12, 8)
		NUM_CLASSES = 37
		
		results = []
		for i in range(batch_size):
			image = Image.open(data[i])
			# the array based representation of the image will be used later in order to prepare the
			# result image with boxes and labels on it.
			image_np = self.load_image_into_numpy_array(image)
			# Expand dimensions since the model expects images to have shape: [1, None, None, 3]
			image_np_expanded = np.expand_dims(image_np, axis=0)
			with self._graph.as_default():
				with self._sess as sess:
					# Get handles to input and output tensors
					ops = tf.get_default_graph().get_operations()
					all_tensor_names = {output.name for op in ops for output in op.outputs}
					tensor_dict = {}
					for key in ['num_detections', 'detection_boxes', 'detection_scores','detection_classes', 'detection_masks']:
						tensor_name = key + ':0'
						if tensor_name in all_tensor_names:
							tensor_dict[key] = tf.get_default_graph().get_tensor_by_name(tensor_name)
					if 'detection_masks' in tensor_dict:
						# The following processing is only for single image
						detection_boxes = tf.squeeze(tensor_dict['detection_boxes'], [0])
						detection_masks = tf.squeeze(tensor_dict['detection_masks'], [0])
						# Reframe is required to translate mask from box coordinates to image coordinates and fit the image size.
						real_num_detection = tf.cast(tensor_dict['num_detections'][0], tf.int32)
						detection_boxes = tf.slice(detection_boxes, [0, 0], [real_num_detection, -1])
						detection_masks = tf.slice(detection_masks, [0, 0, 0], [real_num_detection, -1, -1])
						detection_masks_reframed = utils_ops.reframe_box_masks_to_image_masks(
												detection_masks, detection_boxes, image.shape[0], image.shape[1])
						detection_masks_reframed = tf.cast(tf.greater(detection_masks_reframed, 0.5), tf.uint8)
					# Follow the convention by adding back the batch dimension
					tensor_dict['detection_masks'] = tf.expand_dims(detection_masks_reframed, 0)
					image_tensor = tf.get_default_graph().get_tensor_by_name('image_tensor:0')

					# Run inference
					output_dict = sess.run(tensor_dict, feed_dict={image_tensor: np.expand_dims(image, 0)})
					
					# all outputs are float32 numpy arrays, so convert types as appropriate
					output_dict['num_detections'] = int(output_dict['num_detections'][0])
					output_dict['detection_classes'] = output_dict['detection_classes'][0].astype(np.uint8)
					output_dict['detection_boxes'] = output_dict['detection_boxes'][0]
					output_dict['detection_scores'] = output_dict['detection_scores'][0]
					if 'detection_masks' in output_dict:
						output_dict['detection_masks'] = output_dict['detection_masks'][0]
				
			results.append(str(output_dict['detection_classes']))
			
		return ",".join(results)
	
	
	

		