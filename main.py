
# Import libraries
import os
import json
import torch
import matplotlib.pyplot as plt
from torch.utils.data import Subset, random_split

# Import local modules
from helper_functions import plot_images, count_parameters, check_gradient
from models.unet import UNet
from models.vit import VisionTransformer
from models.conv import ConvolutionalNet
# from models.vae import VariationalAutoencoder
# from models.resnet import ResNet
from training import train_model
# from datasets.bdellovibrio import BdellovibrioDataset
from datasets.retina_FIVES import RetinaDatasetFives

# Set environment
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
outpath = 'outfiles'


# Define training scheme function
def run_training_scheme(
        modelID, dataID, savename,
        ffcvID=0, img_size=128, pretrain=False, 
        trainargs=None, pretrainargs=None, **modelargs
    ):
    """Run a training scheme on a model and dataset with given options."""

    # Set up inputs
    if trainargs is None:
        trainargs = {}
    if pretrainargs is None:
        pretrainargs = {}

    # Get dataset
    if dataID == 'bdellovibrio':
        dataset = BdellovibrioDataset(image_shape=(img_size, img_size))
        in_channels = 3
        out_channels = 2
    elif dataID == 'retina_FIVES':
        dataset = RetinaDatasetFives(crop=(img_size, img_size))
        in_channels = 3
        out_channels = 2
        
    # Get 5-fold cross-validation split from ffcvID
    splits = random_split(dataset, [len(dataset) // 5] * 5)
    testID = ffcvID
    valID = (ffcvID + 1) % 5
    trainIDs = [i for i in range(5) if i not in [testID, valID]]
    dataset_test = Subset(dataset, indices=splits[testID].indices)
    dataset_val = Subset(dataset, indices=splits[valID].indices)
    dataset_train = Subset(dataset, indices=[idx for i in trainIDs for idx in splits[i].indices])
    datasets = (dataset_train, dataset_val, dataset_test)

    # Get model
    if modelID == 'vit':
        model = VisionTransformer(
            img_size=img_size, 
            in_channels=in_channels, 
            out_channels=out_channels,
            **modelargs
        )
        pretrainargs['mae'] = True
    elif modelID == 'unet':
        model = UNet(
            in_channels=in_channels, 
            out_channels=out_channels,
            **modelargs
        )
    elif modelID == 'conv':
        model = ConvolutionalNet(
            in_channels=in_channels, 
            out_channels=out_channels,
            **modelargs
        )

    # Pretrain as autoencoder if necessary
    if pretrain:
        # Modify output layer
        model.set_output_layer(in_channels)

        # Pretrain model
        model, statistics = train_model(
            model, datasets, os.path.join(outpath, f'{savename}_pretrain.pth'),
            segmentation=False, autoencoder=True,
            verbose=True, plot=True, device=device,
            # n_epochs=1,  # TESTING
            **pretrainargs
        )

        # Save statistics as json
        with open(os.path.join(outpath, f'{savename}_pretrain.json'), 'w') as f:
            json.dump(statistics, f)

        # Modify output layer back
        model.set_output_layer(out_channels)
        

    # Train model
    model, statistics = train_model(
        model, datasets, os.path.join(outpath, f'{savename}.pth'),
        segmentation=True,
        verbose=True, plot=True, device=device,
        # n_epochs=1,  # TESTING
        **trainargs
    )

    # Save statistics as json
    with open(os.path.join(outpath, f'{savename}.json'), 'w') as f:
        json.dump(statistics, f)

    # Done
    print('Done.')
    return


# Run training scheme
if __name__ == "__main__":

    # Select parameters
    modelID = 'vit'
    dataID = 'retina_FIVES'
    options = {
        'pretrain': True,
    }

    # Configure savename
    savename = f'{modelID}_{dataID}'
    for key, value in options.items():
        savename += f'_{key}={value}'

    # Run training scheme
    run_training_scheme(modelID, dataID, savename, **options)

    # Done
    print('Done.')

