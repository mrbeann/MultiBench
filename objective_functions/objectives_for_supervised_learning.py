from objective_functions.recon import recon_weighted_sum,elbo_loss
import torch
from objective_functions.cca import CCALoss

def criterioning(pred,truth,criterion):
    if type(criterion)==torch.nn.CrossEntropyLoss:
        return criterion(pred,truth.long().cuda())
    elif type(criterion)==torch.nn.modules.loss.BCEWithLogitsLoss or type(criterion)==torch.nn.MSELoss:
        return criterion(pred,truth.float().cuda())

def MFM_objective(ce_weight,modal_loss_funcs,recon_weights,input_to_float=True,criterion=torch.nn.CrossEntropyLoss()):
    recon_loss_func = recon_weighted_sum(modal_loss_funcs,recon_weights)
    def actualfunc(pred,truth,args):
        ints = args['intermediates']
        reps = args['reps']
        fused = args['fused']
        decoders = args['decoders']
        inps = args['inputs']
        recons = []
        for i in range(len(reps)):
            recons.append(decoders[i](torch.cat([ints[i](reps[i]),fused],dim=1)))
        ce_loss = criterioning(pred,truth,criterion)
        if input_to_float:
            inputs = [i.float().cuda() for i in inps]
        else:
            inputs = [i.cuda() for i in inps]
        recon_loss = recon_loss_func(recons,inputs)
        return ce_loss*ce_weight+recon_loss
    return actualfunc

def reparameterize(mu, logvar, training):
    if training:
        std = logvar.mul(0.5).exp_()
        eps = torch.autograd.Variable(std.data.new(std.size()).normal_())
        return eps.mul(std).add_(mu)
    else:
        return mu

def MVAE_objective(ce_weight,modal_loss_funcs,recon_weights,input_to_float=True,annealing=1.0,criterion=torch.nn.CrossEntropyLoss()):
    recon_loss_func = elbo_loss(modal_loss_funcs,recon_weights,annealing)
    def allnonebuti(i,item):
        ret=[None for w in modal_loss_funcs]
        ret[i]=item
        return ret
    def actualfunc(pred,truth,args):
        training = args['training']
        reps = args['reps']
        fusedmu,fusedlogvar = args['fused']
        decoders = args['decoders']
        inps = args['inputs']
        reconsjoint = []
        
        if input_to_float:
            inputs = [i.float().cuda() for i in inps]
        else:
            inputs = [i.cuda() for i in inps]
        for i in range(len(inps)):
            reconsjoint.append(decoders[i](reparameterize(fusedmu,fusedlogvar,training)))
        total_loss = recon_loss_func(reconsjoint,inputs,fusedmu,fusedlogvar)
        for i in range(len(inps)):
            mu,logvar = reps[i]
            recon = decoders[i](reparameterize(mu,logvar,training))
            total_loss += recon_loss_func(allnonebuti(i,recon),allnonebuti(i,inputs[i]),mu,logvar)
        total_loss += ce_weight * criterioning(pred,truth,criterion)
        return total_loss
    return actualfunc

def CCA_objective(out_dim,cca_weight=0.001,criterion=torch.nn.CrossEntropyLoss()):
    lossfunc = CCALoss(out_dim,False, device=torch.device("cuda"))
    def actualfunc(pred,truth,args):
        ce_loss = criterioning(pred,truth,criterion)
        outs = args['reps']
        cca_loss = lossfunc(outs[0],outs[1])
        return cca_loss * cca_weight + ce_loss
    return actualfunc

def RefNet_objective(ref_weight,criterion=torch.nn.CrossEntropyLoss(),input_to_float=True):
    ss_criterion=torch.nn.CosineEmbeddingLoss()
    def actualfunc(pred,truth,args):
        ce_loss = criterioning(pred,truth,criterion)
        refiner = args['refiner']
        fused = args['fused']
        inps = args['inputs']
        refinerout = refiner(fused)
        if input_to_float:
            inputs = [torch.flatten(t,start_dim=1).float().cuda() for t in inps]
        else:
            inputs = [torch.flatten(t,start_dim=1).cuda() for t in inps]

        inputsizes = [t.size(1) for t in inputs]
        ss_loss=0.0
        loc=0
        for i in range(len(inps)):
            out = refinerout[:,loc:loc+inputsizes[i]]
            loc += inputsizes[i]
            ss_loss += ss_criterion(out,inputs[i],torch.ones(out.size(0)).cuda())
        return ce_loss + ss_loss*ref_weight
    return actualfunc
