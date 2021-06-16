import sys
import os
sys.path.append(os.getcwd())

import torch

from training_structures.Supervised_Learning import train, test
from fusions.common_fusions import LowRankTensorFusion
from datasets.imdb.get_data import get_dataloader
from unimodals.common_models import MaxOut_MLP, Linear

filename = "best_lrtf.pt"
traindata, validdata, testdata = get_dataloader('../video/multimodal_imdb.hdf5', '../video/mmimdb', vgg=True, batch_size=128)

encoders=[MaxOut_MLP(512, 512, 300, linear_layer=False), MaxOut_MLP(512, 1024, 4096, 512, False)]
head= Linear(512, 23).cuda()
fusion=LowRankTensorFusion([512,512],512,128).cuda()

train(encoders,fusion,head,traindata,validdata,1000, early_stop=True,task="multilabel",\
    save=filename, optimtype=torch.optim.AdamW,lr=8e-3,weight_decay=0.01, objective=torch.nn.BCEWithLogitsLoss())

print("Testing:")
model=torch.load(filename).cuda()
test(model,testdata,dataset='mmimdb',criterion=torch.nn.BCEWithLogitsLoss(),task="multilabel")


