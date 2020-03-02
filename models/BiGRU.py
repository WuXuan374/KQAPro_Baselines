import torch
import torch.nn as nn

class GRU(nn.Module):

    def __init__(self, dim_word, dim_h, num_layers, dropout):
        super().__init__()
        self.encoder = nn.GRU(input_size=dim_word,
                hidden_size=dim_h,
                num_layers=num_layers,
                dropout=dropout,
                batch_first=True,
                bidirectional=False)

    def forward_one_step(self, input, last_h):
        """
        Args:
            - input (bsz, 1, w_dim)
            - last_h (num_layers, bsz, h_dim)
        """
        hidden, new_h = self.encoder(input, last_h)
        return hidden, new_h  # (bsz, 1, h_dim), (num_layers, bsz, h_dim)


    def forward(self, input, length, h_0=None):
        """
        Args:
            - input (bsz, len, w_dim)
            - length (bsz, )
            - h_0 (num_layers, bsz, h_dim)
        Return:
            - hidden (bsz, len, dim) : hidden state of each word
            - output (bsz, dim) : sentence embedding
        """
        bsz, max_len = input.size(0), input.size(1)
        sorted_seq_lengths, indices = torch.sort(length, descending=True)
        _, desorted_indices = torch.sort(indices, descending=False)
        input = input[indices]
        packed_input = nn.utils.rnn.pack_padded_sequence(input, sorted_seq_lengths, batch_first=True)
        if h_0 is None:
            hidden, h_n = self.encoder(packed_input) 
        else:
            h_0 = h_0[:, indices]
            hidden, h_n = self.encoder(packed_input, h_0)
        # h_n is (num_layers, bsz, h_dim)
        hidden = nn.utils.rnn.pad_packed_sequence(hidden, batch_first=True, total_length=max_len)[0] # (bsz, max_len, h_dim)
        
        output = h_n[-1, :, :] # (bsz, h_dim), take the last layer's state

        # recover order
        hidden = hidden[desorted_indices]
        output = output[desorted_indices]
        h_n = h_n[:, desorted_indices]
        return hidden, output, h_n



class BiGRU(nn.Module):

    def __init__(self, dim_word, dim_h, num_layers, dropout):
        super().__init__()
        self.encoder = nn.GRU(input_size=dim_word,
                hidden_size=dim_h//2,
                num_layers=num_layers,
                dropout=dropout,
                batch_first=True,
                bidirectional=True)

    def forward(self, input, length):
        """
        Args:
            - input (bsz, len, w_dim)
            - length (bsz, )
        Return:
            - hidden (bsz, len, dim) : hidden state of each word
            - output (bsz, dim) : sentence embedding
            - h_n (num_layers * 2, bsz, dim//2)
        """
        bsz, max_len = input.size(0), input.size(1)
        sorted_seq_lengths, indices = torch.sort(length, descending=True)
        _, desorted_indices = torch.sort(indices, descending=False)
        input = input[indices]
        packed_input = nn.utils.rnn.pack_padded_sequence(input, sorted_seq_lengths, batch_first=True)
        hidden, h_n = self.encoder(packed_input) 
        # h_n is (num_layers * num_directions, bsz, h_dim//2)
        hidden = nn.utils.rnn.pad_packed_sequence(hidden, batch_first=True, total_length=max_len)[0] # (bsz, max_len, h_dim)
        
        output = h_n[-2:, :, :] # (2, bsz, h_dim//2), take the last layer's state
        output = output.permute(1, 0, 2).contiguous().view(bsz, -1) # (bsz, h_dim), merge forward and backward h_n

        # recover order
        hidden = hidden[desorted_indices]
        output = output[desorted_indices]
        h_n = h_n[:, desorted_indices]
        return hidden, output, h_n
