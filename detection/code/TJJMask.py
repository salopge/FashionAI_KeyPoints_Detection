# -- coding: utf-8 --
import os
import sys
import random
import math
import re
import time
import numpy as np
import matplotlib
import pandas as pd
import tensorflow as tf
from config import Config
import utils2
import model as modellib
# import visualize
from model import log
from PIL import Image
import csv
import cv2

# Root directory of the project
ROOT_DIR = '../'

#piont names and class name
'''添加fashion ai'''
fi_class_names = [sys.argv[1]]

# Directory to save logs and trained model
MODEL_DIR = os.path.join(ROOT_DIR, "logs/{}_logs".format(fi_class_names[0]))
model_path = os.path.join(ROOT_DIR, "model/mask_rcnn_{}.h5".format(fi_class_names[0]))
result_save_path='../submit/{}_test_result.csv'.format(fi_class_names[0])
#result_save_path=('./data/test/{0}_result.csv'.format(fi_class_names[0]))


class_names_ = ['neckline_left', 'neckline_right', 'center_front', 'shoulder_left',
                   'shoulder_right', 'armpit_left', 'armpit_right', 'waistline_left',
                   'waistline_right', 'cuff_left_in', 'cuff_left_out', 'cuff_right_in',
                   'cuff_right_out', 'top_hem_left', 'top_hem_right', 'waistband_left',
                   'waistband_right', 'hemline_left', 'hemline_right', 'crotch',
                   'bottom_left_in', 'bottom_left_out', 'bottom_right_in', 'bottom_right_out']
'''
各类存在的点在class_names_中的索引
'''
blouse_index=[0,1,2,3,4,5,6,9,10,11,12,13,14]#NUM_KEYPOINTS=13
skirt_index=[15,16,17,18]#NUM_KEYPOINTS=4
outwear_index=[0,1,3,4,5,6,7,8,9,10,11,12,13,14]#NUM_KEYPOINTS=14
dress_index=[0,1,2,3,4,5,6,7,8,9,10,11,12,17,18]#NUM_KEYPOINTS=15
trousers_index=[15,16,19,20,21,22,23]#NUM_KEYPOINTS=7


all_index={'blouse':blouse_index,
           'skirt':skirt_index,
           'outwear':outwear_index,
           'dress':dress_index,
           'trousers':trousers_index}
index = all_index[fi_class_names[0]]

fi_class_names_=[]
for i in index:
    fi_class_names_.append(class_names_[i])
print(fi_class_names_)

#############################################
#
#############################################
def pic_height_width(filepath):
    fp = open(filepath, 'rb')
    im = Image.open(fp)
    fp.close()
    x, y = im.size
    if(im.mode =='RGB'):
        return x,y
    else:
        return False,False


class InferenceConfig(Config):
  # Give the configuration a recognizable name
    NAME = "FI"

    # Train on 1 GPU and 8 images per GPU. We can put multiple images on each
    # GPU because the images are small. Batch size is 8 (GPUs * images/GPU).
    GPU_COUNT = 1
    IMAGES_PER_GPU = 1
    NUM_KEYPOINTS = len(all_index[fi_class_names[0]])
    KEYPOINT_MASK_SHAPE = [56, 56]
    # Number of classes (including background)
    NUM_CLASSES = 1 + 1 # background + 24 key_point

    RPN_TRAIN_ANCHORS_PER_IMAGE = 150
    VALIDATION_STPES = 100
    STEPS_PER_EPOCH = 100
    MINI_MASK_SHAPE = (56, 56)
    KEYPOINT_MASK_POOL_SIZE = 7
            # Pooled ROIs
    POOL_SIZE = 7
    MASK_POOL_SIZE = 14
    MASK_SHAPE = [28, 28]
    WEIGHT_LOSS = True
    KEYPOINT_THRESHOLD = 0.005
    # Maximum number of ground truth instances to use in one image
    MAX_GT_INSTANCES = 128


    DETECTION_MAX_INSTANCES = 1

'''
test data set class
'''
class FITestDataset(utils2.Dataset):
    def load_FI_test(self):
        test_data_path='/home/tanghm/Documents/YFF/TJJ/base_fusai'
        # Add classes
        for i, class_name in enumerate(fi_class_names):
            self.add_class("FI", i + 1, class_name)
        annotations = pd.read_csv('/home/tanghm/Documents/YFF/TJJ/base_fusai/Annotations/label_length.csv')
        annotations = annotations.loc[annotations['image_category'] == sys.argv[2]]

        annotations = annotations.reset_index(drop=True)  # 更新索引

        for x in range(annotations.shape[0]):
            # bg_color, shapes = self.random_image(height, width)
            id = annotations.loc[x, 'image_id']
            category = annotations.loc[x, 'image_category']
            #print('loading image:%d/%d'%(x,annotations.shape[0]))
            im_path = os.path.join(test_data_path, id)
            # height, width = cv2.imread(im_path).shape[0:2]
            width, height = pic_height_width(im_path)
            self.add_image("FI", image_id=id, path=im_path,
                           width=width, height=height,
                            image_category=category)  # 添加我的数据
    def load_image(self, image_id):
        """Generate an image from the specs of the given image ID.
        Typically this function loads the image from a file, but
        in this case it generates the image on the fly from the
        specs in image_info.
        根据image_id读取图片
        """
        info = self.image_info[image_id]
        # image = cv2.imread(info['path'])
        image = Image.open(info['path'])
        image = np.array(image)
        return image
###############################################################
'''
把int类型转为num_num_num格式以便提交
'''
def keypoint_to_str(keypoint):
    keypoint = keypoint.reshape([len(class_names_), 3])
    for x in range(len(class_names_)):
        if keypoint[x][2] != 1:
            keypoint[x] = [-1, -1, -1]
    list_keypoint = []
    for x in keypoint:
        list_keypoint.append(str(x[0]) + '_' + str(x[1]) + '_' + str(x[2]))
    return list_keypoint


'''
把得到的结果映射到24个点中。
'''
def keypoint_map_to24(points,img_category):
    x=[[-1,-1,-1] for i in range(24)]
    for point_index,x_index in enumerate(all_index[img_category]):
        #print(point_str_index)
        x[x_index]=points[point_index]
    return np.array(x)



if __name__ =='__main__':
    print(sys.argv[0])
    dataset_test=FITestDataset()
    dataset_test.load_FI_test()
    dataset_test.prepare()

    #config of model
    inference_config = InferenceConfig()

    # Recreate the model in inference mode
    model = modellib.MaskRCNN(mode="inference",
                              config=inference_config,
                              model_dir=MODEL_DIR)

    # Get path to saved weights
    # Load trained weights (fill in path to trained weights here)
    assert model_path != "", "Provide path to trained weights"
    print("Loading weights from ", model_path)
    model.load_weights(model_path, by_name=True)

    ###########################################################################
    #保存结果到csv dataset_test.num_images
    ###########################################################################
    point_to_csv_list=[['image_id','image_category','roiPoint']]#设置columns]

    error_count = 0
    for x in range(0,dataset_test.num_images):
        image=dataset_test.load_image(x) #0为图像id
        image = cv2.resize(image,(512,512),interpolation=cv2.INTER_CUBIC)
        category=dataset_test.image_info[x]['image_category'] #图像类别
        image_id=dataset_test.image_info[x]['id']
        # print(image.dtype)
        results = model.detect_keypoint([image], verbose=0)

        r = results[0]  # for one image
        # log("image", image)
        # log("rois", r['rois'])
        # log("keypoints", r['keypoints'])
        # log("class_ids", r['class_ids'])
        # log("keypoints", r['keypoints'])
        h, w, _ = image.shape

        try:#统计未检测出目标的图片
            key_points = keypoint_map_to24(r['keypoints'][0], fi_class_names[0])
        except:
            key_points =np.array([[[0,0,0] for i in range(24)]])
            r['rois'] = np.array([[0,0,h,w]])
            error_count+=1
            ####把有问题的图片记录下来
            # with open('./notdetection.txt', 'a') as f:
            #     f.write(sys.argv[1] + '/' + image_id + '\n')

        # visualize.display_keypoints(image,r['rois'],r['keypoints'], r['class_ids'], dataset_test.class_names)

        # point_str=keypoint_to_str(key_points)#把坐标转为字符
        # print(point_str)
        ###########################################################################################
        # print(image_id,error_count)
        pad = 35
        up = 35
        left = 35
        right = 35
        down = 35
        y1 = r['rois'][0][0]
        x1 = r['rois'][0][1]
        y2 = r['rois'][0][2]
        x2 = r['rois'][0][3]
        if (y1 - pad < 0):
            up = y1
        if (x1 - pad) < 0:
            left = x1
        if (y2 + pad > h):
            down = h-y2
        if (x2 + pad > w):
            right = w-x2
        newImage = image[int(y1 - up):int(y2 + pad + 80), int(x1 - left):int(x2 + pad)]
        roiPoint = np.zeros((1, 4))
        roiPoint[0][0] = int(y1 - up)
        roiPoint[0][1] = int(x1 - left)
        roiPoint[0][2] = int(y2 + down)
        roiPoint[0][3] = int(x2 + right)
        str_point = str(int(roiPoint[0][0]))+'_'+str(int(roiPoint[0][1]))+'_'+str(int(roiPoint[0][2]))+'_'+str(int(roiPoint[0][3]))
        # print(str_point)
        print(image_id,error_count,roiPoint,str(x)+'/'+str(dataset_test.num_images))
        imagName = image_id.split('/')[2]
        saveImg = image[int(roiPoint[0][0]):int(roiPoint[0][2]),int(roiPoint[0][1]):int(roiPoint[0][3])]
        saveImg = cv2.cvtColor(saveImg, 4)
        # image = cv2.cvtColor(image, 4)
        cv2.imwrite(sys.argv[3]+imagName, saveImg)
        # cv2.imwrite('./testori' + str(x) + '.jpg',image)
        ###########################################################################################
        relust_info=[image_id,category,str_point]

        # relust_info.append(str_point)
        point_to_csv_list.append(relust_info)
        # print(error_count, r'/', x, r'/', dataset_test.num_images)

    '''
    保存结果
    '''

    # columns.extend(class_names_)      #
    # print(point_to_csv_list)
    # with open(result_save_path, 'w') as f:
    #     writer = csv.writer(f)
    #     writer.writerows(point_to_csv_list)
    # point_to_csv=pd.DataFrame(data=np.array(point_to_csv_list).reshape([-1,3]),
    #                           columns=columns)
    # point_to_csv.to_csv(result_save_path,index=False)
