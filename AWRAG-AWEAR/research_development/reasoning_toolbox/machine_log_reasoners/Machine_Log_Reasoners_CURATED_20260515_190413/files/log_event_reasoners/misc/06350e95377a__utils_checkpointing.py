import torch
import logging

def save_checkpoint(model, optimizer, epoch, path, val_loss):
    """
    Saves a model checkpoint.
    """
    torch.save({
        'epoch': epoch,
        'val_loss': val_loss,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
    }, path)
    logging.info(f"Checkpoint saved at {path} with validation loss: {val_loss:.4f}")

def load_checkpoint(model, optimizer, path):
    """
    Loads a model checkpoint.
    """
    checkpoint = torch.load(path)
    model.load_state_dict(checkpoint['model_state_dict'])
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    logging.info(f"Checkpoint loaded from {path}")
