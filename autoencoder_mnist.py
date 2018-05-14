# Simple MNIST autoencoder using TensorFlow
# Reference: https://gertjanvandenburg.com/blog/autoencoder/

import numpy as np
import tensorflow as tf

from magenta.models.image_stylization.image_utils import form_image_grid
from tensorflow.examples.tutorials.mnist import input_data

BATCH_SIZE = 50
GRID_ROWS = 5
GRID_COLS = 10


def weight_variable(shape):
    initial = tf.truncated_normal(shape, stddev=0.1)
    return tf.Variable(initial)

def bias_variable(shape):
    initial = tf.constant(0.1, shape=shape)
    return tf.Variable(initial)

def fc_layer(prev, input_size, output_size):
    W = weight_variable([input_size, output_size])
    b = bias_variable([output_size])
    return tf.matmul(prev, W) + b

def autoencoder(x):
    layer1 = tf.nn.tanh(fc_layer(x, 28 * 28, 50))
    layer2 = tf.nn.tanh(fc_layer(layer1, 50, 50))
    layer3 = fc_layer(layer2, 50, 2)
    layer4 = tf.nn.tanh(fc_layer(layer3, 2, 50))
    layer5 = tf.nn.tanh(fc_layer(layer4, 50, 50))
    output = fc_layer(layer5, 50, 28 * 28)
    loss = tf.reduce_mean(tf.squared_difference(x, output))
    return loss, output, layer3

def layer_grid_summary(name, var, image_dims):
    prod = np.prod(image_dims)
    grid = form_image_grid(tf.reshape(var, [BATCH_SIZE, prod]), [GRID_ROWS, GRID_COLS], image_dims, 1)
    return tf.summary.image(name, grid)

def create_summaries(loss, x, latent, output):
    writer = tf.summary.FileWriter("./logs")
    tf.summary.scalar("Loss", loss)
    layer_grid_summary("Input", x, [28, 28])
    layer_grid_summary("Encoder", latent, [2, 1])
    layer_grid_summary("Output", output, [28, 28])
    return writer, tf.summary.merge_all()

def make_image(name, var, image_dims):
    prod = np.prod(image_dims)
    grid = form_image_grid(tf.reshape(var, [BATCH_SIZE, prod]), [GRID_ROWS,
        GRID_COLS], image_dims, 1)
    s_grid = tf.squeeze(grid, axis=0)

    # This reproduces the code in: tensorflow/core/kernels/summary_image_op.cc
    im_min = tf.reduce_min(s_grid)
    im_max = tf.reduce_max(s_grid)

    kZeroThreshold = tf.constant(1e-6)
    max_val = tf.maximum(tf.abs(im_min), tf.abs(im_max))

    offset = tf.cond(
            im_min < tf.constant(0.0),
            lambda: tf.constant(128.0),
            lambda: tf.constant(0.0)
            )
    scale = tf.cond(
            im_min < tf.constant(0.0),
            lambda: tf.cond(
                max_val < kZeroThreshold,
                lambda: tf.constant(0.0),
                lambda: tf.div(127.0, max_val)
                ),
            lambda: tf.cond(
                im_max < kZeroThreshold,
                lambda: tf.constant(0.0),
                lambda: tf.div(255.0, im_max)
                )
            )
    s_grid = tf.cast(tf.add(tf.multiply(s_grid, scale), offset), tf.uint8)
    enc = tf.image.encode_jpeg(s_grid)

    fwrite = tf.write_file(name, enc)
    return fwrite

def main():
    mnist = input_data.read_data_sets('./MNIST_data')
    x = tf.placeholder(tf.float32, shape=[None, 28 * 28])
    loss, output, latent = autoencoder(x)
    train_step = tf.train.AdamOptimizer(1e-5).minimize(loss)
    writer, summary_op = create_summaries(loss, x, latent, output)

    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())
        for i in range(100000):
            batch = mnist.train.next_batch(BATCH_SIZE)
            feed = {x: batch[0]}
            if i % 500 == 0:
                summary, train_loss = sess.run([summary_op, loss], feed_dict=feed)
                print('Step: %d, Loss: %g' % (i, train_loss))
                writer.add_summary(summary, i)
                writer.flush()
            if i % 1000 == 0:
                sess.run(make_image("images/output_%06i.jpg" % i, output, [28,
                    28]), feed_dict={x : batch[0]})
            train_step.run(feed_dict=feed)

if __name__ == '__main__':
    main()
