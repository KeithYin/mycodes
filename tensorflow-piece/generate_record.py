"""
This is used for generate TFRecord, if you want to using this Util, You need to do the following preprocessing steps:

1. Resize all the image to same size.

2. Generate the train_txt file and the test_txt file.The file like that
	img1_relative_path label1
	img2_relative_path label2
	...
3. You need to make sure "data_dir/img1_relative_path" is the absolute path of img1

4. The Funciton read_data is a example to read the tfrecord data
"""
import tensorflow as tf
import os
from matplotlib.pyplot import imread
import argparse
import progressbar


class Img(object):
    def __init__(self, img_path, label):
        self.img_path = img_path
        self.label = label


def _int64_feature(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))


def _bytes_feature(value):
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))


def convert_to(img_list, target_dir, name="train"):
    """
    build records file
    :param img_list: a list of Img objects generated by 'parse_txt_file'
    :param target_dir: the target directory that you want to save the records file
    :param name: using to specify the record file's name. the generated file name is 'name.tfrecords'
    :return: Nothing
    """
    if not isinstance(img_list, list):
        raise ValueError("img_list must be a list")

    total_num = len(img_list)

    ####
    widgets = [ "processing: " ,progressbar.Percentage(),
                " ", progressbar.ETA(),
                " ", progressbar.FileTransferSpeed(),
    ]
    bar = progressbar.ProgressBar(widgets=widgets, max_value=total_num).start()
    ####
    
    
    filename = os.path.join(target_dir, name+'.tfrecords')
    print('Writing', filename)
    writer = tf.python_io.TFRecordWriter(filename)
    for i, img in enumerate(img_list):
        bar.update(i)
        img_data = imread(img.img_path)
        height = img_data.shape[0]
        width = img_data.shape[1]
        depth = img_data.shape[2]
        img_data_raw = img_data.tostring()
        example = tf.train.Example(features=tf.train.Features(feature={
            'height': _int64_feature(height),
            'width': _int64_feature(width),
            'depth': _int64_feature(depth),
            'label': _int64_feature(int(img.label)),
            'image_raw': _bytes_feature(img_data_raw)}))
        writer.write(example.SerializeToString())
    writer.close()
    bar.finish()
    print("done")



def parse_txt_file(file_name, data_dir):
    """
    using txt file and data root dir to generate a list of Img object using to build records
    :param file_name: train_txt file name or test_txt file name
    :param data_dir: data root dir, using to generate the absolute path of the image
    :return: a list of Img objects
    """
    imgs = []
    with open(file_name, mode="r") as file:
        try:
            for line in file:
                img_label = line.split(" ")

                img_path = os.path.join(data_dir, img_label[0])
                label = int(img_label[1])
                imgs.append(Img(img_path, label))
        except KeyboardInterrupt as e:
            file.close()
    return imgs


def read_data(file_names, batch_size):
	"""
	Using to read a mini-batch from the tfrecords.
    :param file_names: specify the tfrecords file names
    :param batch_size: batch size
    :return: a tuple of (example_batch, label_batch)
	"""
    if isinstance(file_names, str):
        file_names = [file_names]
    assert isinstance(file_names, list)

    with tf.name_scope("InputPipeLine"):
        file_name_queue = tf.train.string_input_producer(file_names, num_epochs=10000, shuffle=True)

        # prepare reader
        reader = tf.TFRecordReader()
        key, record_string = reader.read(file_name_queue)
        features = tf.parse_single_example(record_string,features={
                                           'height': tf.FixedLenFeature([],tf.int64),
                                            'width': tf.FixedLenFeature([], tf.int64),
                                            'depth': tf.FixedLenFeature([], tf.int64),
                                            'label': tf.FixedLenFeature([], tf.int64),
                                            'image_raw': tf.FixedLenFeature([],tf.string)})
        img = tf.decode_raw(features['image_raw'], tf.float32)
        height = tf.cast(features['height'], tf.int32)
        width = tf.cast(features['width'], tf.int32)
        depth = tf.cast(features['depth'], tf.int32)
        label = tf.cast(features['label'], tf.int32)
        img_shape = tf.stack([height, width, depth])
        img_reshaped = tf.cast(tf.reshape(img,[224,224,3]), tf.float32)

        min_after_dequeue = 500
        capacity = min_after_dequeue+3*batch_size

        example_batch, label_batch = tf.train.shuffle_batch([img_reshaped, label],
                                                            batch_size=batch_size,min_after_dequeue=min_after_dequeue,
                                                            num_threads=4, capacity=capacity)
        return example_batch, label_batch

        
def main(args):
    train_imgs = parse_txt_file(args.train_txt, args.data_dir)
    test_imgs = parse_txt_file(args.test_txt, args.data_dir)
    convert_to(train_imgs,target_dir=args.target_dir, name="train")
    convert_to(test_imgs, target_dir=args.target_dir, name="test")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Utils to build TF record")
    parser.add_argument("--data_dir", default="", help="the data root dir")
    parser.add_argument("--train_txt",default="", help="train_txt file")
    parser.add_argument("--test_txt", default="", help="test txt file")
    parser.add_argument("--target_dir", default="", help="target dir")
    args = parser.parse_args()
    if args.data_dir=="" or args.train_txt=="" or args.test_txt=="" or args.target_dir=="":
        raise ValueError("you must specify --data_dir, --train_txt, --test_txt, --target_dir")
    main(args)