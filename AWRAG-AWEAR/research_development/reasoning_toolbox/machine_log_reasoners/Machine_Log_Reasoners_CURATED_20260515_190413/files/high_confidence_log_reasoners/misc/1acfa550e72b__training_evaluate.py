from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

def evaluate(model, val_dataloader, device):
    """
    Evaluates the model's performance and logs metrics.
    """
    model.eval()
    all_preds, all_labels = [], []
    total_loss = 0
    loss_fn = nn.CrossEntropyLoss()

    with torch.no_grad():
        for batch in val_dataloader:
            input_ids, attention_mask, labels = (
                batch['input_ids'].to(device),
                batch['attention_mask'].to(device),
                batch['labels'].to(device),
            )
            outputs = model(input_ids, attention_mask)
            preds = torch.argmax(outputs, dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            total_loss += loss_fn(outputs, labels).item()

    acc = accuracy_score(all_labels, all_preds)
    f1 = f1_score(all_labels, all_preds, average='weighted')
    precision = precision_score(all_labels, all_preds, average='weighted')
    recall = recall_score(all_labels, all_preds, average='weighted')

    print(f"Accuracy: {acc * 100:.2f}%, F1: {f1:.2f}, Precision: {precision:.2f}, Recall: {recall:.2f}")
    return total_loss / len(val_dataloader)
