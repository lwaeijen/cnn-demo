#!/usr/bin/env python
import caffe
import numpy as np
import argparse
import logging


def feed_fwd(
        prototxt,
        caffemodel,
        image,
        logger,
        dump_buffers=False,
        dump_weights=False,
        scale=1.0,
    ):

    def san(s):
        return s.replace('/','_')

    # Use CPU for verification
    caffe.set_mode_cpu()

    # load caffe network
    net = caffe.Net(
        prototxt,
        caffemodel,
        caffe.TEST
    )


    #dump weights and biases
    if dump_weights:
        for lyr_name, param in net.params.iteritems():

            fname=san(lyr_name)+'_weights.bin'
            with open(fname, 'wb') as f:
                logger.info("Writing weights of layer %s to file %s"%(lyr_name, fname))
                logger.debug(lyr_name, 'weights', param[0].data.shape)
                f.write(param[0].data)

            fname=san(lyr_name)+'_bias.bin'
            with open(fname, 'wb') as f:
                logger.info("Writing bias of layer %s to file %s"%(lyr_name, fname))
                logger.debug(lyr_name, 'bias', param[1].data.shape)
                f.write(param[1].data)


    # Create transformer for the input called 'data'
    transformer = caffe.io.Transformer({'data': net.blobs['data'].data.shape})
    transformer.set_transpose('data', (2,0,1))                              # move image channels to outermost dimension
    transformer.set_raw_scale('data', 255.0)                                # rescale from [0, 1] to [0, 255]
    transformer.set_mean('data', np.array([103.939,116.779,123.68]))        # subtract the dataset-mean value in each channel (RGB)
    transformer.set_channel_swap('data', (2,1,0))                           # swap channels from RGB to BGR
    transformer.set_input_scale('data', scale)

    def inference(fname):
        image = caffe.io.load_image(fname)
        transformed_image = transformer.preprocess('data', image)

        net.blobs['data'].data[...] = transformed_image
        output = net.forward()
        output_prob = output['prob'][0] #output probability of first image in the batch

        return output_prob.argmax()


    logger.info("Loading image %s"%(image))
    image = caffe.io.load_image(image)

    logger.info("Transforming input data by subtracting the dataset-mean for image net and scaling to [0-255]")
    transformed_image = transformer.preprocess('data', image)

    #set transformed image as input to the network
    net.blobs['data'].data[...] = transformed_image

    logger.info("Start feedforward")
    output = net.forward()
    logger.info("End of feedforward")

    if dump_buffers:
        for lyr_name, blob in net.blobs.iteritems():
            fname=san(lyr_name)+'_buf.txt'
            logger.info("Dumping buffer of layer %s to file %s"%(lyr_name, fname))
            with open(fname, 'wt') as f:
                shape = tuple(blob.data.shape)
                if len(shape)==2:
                    batch, z = shape
                    for o in xrange(z):
                        f.write("%f\n"%(blob.data.item(0,o)))
                else:
                    batch, z, y, x = shape
                    for o in xrange(z):
                        for m in xrange(y):
                            for n in xrange(x):
                                f.write("%f\n"%(blob.data.item(0,o,m,n)))

    #output probability of first image in the batch
    output_prob = output['prob'][0]
    logger.info("Index of largest output is \"%s\", with value \"%s\""%(str(output_prob.argmax()), str(output_prob[output_prob.argmax()])))

    #return index of max
    return output_prob.argmax()

def get_args():
    parser = argparse.ArgumentParser()

    # Add verbose levels
    _LOG_LEVEL_STRINGS = ['ERROR','WARNING', 'INFO', 'DEBUG']
    def _log_level_string_to_int(log_level_string):
        if not log_level_string in _LOG_LEVEL_STRINGS:
            message = 'invalid choice: {0} (choose from {1})'.format(log_level_string, _LOG_LEVEL_STRINGS)
            raise argparse.ArgumentTypeError(message)
        log_level_int = getattr(logging, log_level_string, logging.ERROR)
        # check the logging log_level_choices have not changed from our expected values
        assert isinstance(log_level_int, int)
        return log_level_int
    parser.add_argument('--log-level',
    	default='INFO',
    	dest='log_level',
    	type=_log_level_string_to_int,
    	nargs='?',
    	help='Set the logging output level. {0}'.format(_LOG_LEVEL_STRINGS)
    )

    #other arguments
    parser.add_argument('--caffe-prototxt', dest='caffeprototxt', required=True,
        help="Caffe prototxt file",
    )
    parser.add_argument('--caffe-model', dest='caffemodel', required=True,
        help="Caffe model file",
    )
    parser.add_argument('--image', dest='image', required=True,
        help="Input image",
    )
    parser.add_argument('--scale', dest='scale', required=False, default=1.0,type=float,
        help="Input scaling (Mobilenets require scale=0.017)",
    )
    parser.add_argument('--dump-weights', dest='dump_weights', required=False, action='store_true', default=False,
        help="Dump weights and bias values of all convolutional layers"
    )
    parser.add_argument('--dump-buffers', dest='dump_buffers', required=False, action='store_true', default=False,
        help="Dump all intermediate buffers for debugging"
    )

    # Parse arguments
    args = parser.parse_args()

    # Init logger
    logging.basicConfig(level=args.log_level)
    args.logger = logging.getLogger()

    # Return tuple with arguments and logger instance
    return args



if __name__ == '__main__':
    import argparse


    args = get_args()

    argmax=feed_fwd(
        args.caffeprototxt,
        args.caffemodel,
        args.image,
        args.logger,
        dump_buffers=args.dump_buffers,
        dump_weights=args.dump_weights,
        scale=args.scale
    )
