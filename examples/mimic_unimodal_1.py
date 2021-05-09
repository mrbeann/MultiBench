import sys
import os
sys.path.append(os.getcwd())
from training_structures.unimodal import train, test
from datasets.mimic.get_data import get_dataloader
from unimodals.common_models import MLP, GRU
from torch import nn
import torch

#get dataloader for icd9 classification task 7
traindata, validdata, testdata = get_dataloader(1, imputed_path='datasets/mimic/im.pk')
modalnum =1 
#build encoders, head and fusion layer
#encoders = [MLP(5, 10, 10,dropout=False).cuda(), GRU(12, 30,dropout=False).cuda()]
encoder = GRU(12,30,flatten=True).cuda()
head = MLP(720, 40, 6, dropout=False).cuda()


#train
train(encoder, head, traindata, validdata, 20, auprc=True,modalnum=modalnum)

#test
print("Testing: ")
encoder = torch.load('encoder.pt').cuda()
head = torch.load('head.pt').cuda()
test(encoder,head , testdata, auprc=True, modalnum=modalnum)
