import torch.nn as nn
import torch
from spikingjelly.clock_driven import layer

__all__ = [
    'PreActResNet', 'res18', 'res34', 'spiking_testnet_3', 'spiking_testnet_5', 'spiking_testnet_9'
]


class PreActBlock(nn.Module):
    '''Pre-activation version of the BasicBlock.'''
    expansion = 1

    def __init__(self, in_channels, out_channels, stride, dropout, neuron: callable = None, **kwargs):
        super(PreActBlock, self).__init__()
        whether_bias = True
        self.bn1 = nn.BatchNorm2d(in_channels)

        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=whether_bias)
        self.bn2 = nn.BatchNorm2d(out_channels)

        self.dropout = layer.Dropout(dropout)
        self.conv2 = nn.Conv2d(out_channels, self.expansion * out_channels, kernel_size=3, stride=1, padding=1, bias=whether_bias)

        if stride != 1 or in_channels != self.expansion * out_channels:
            self.shortcut = nn.Conv2d(in_channels, self.expansion * out_channels, kernel_size=1, stride=stride, padding=0, bias=whether_bias)
        else:
            self.shortcut = nn.Sequential()

        self.relu1 = neuron(**kwargs)
        self.relu2 = neuron(**kwargs)

    def forward(self, x):
        x = self.relu1(self.bn1(x))
        out = self.conv1(x)
        out = self.conv2(self.dropout(self.relu2(self.bn2(out))))
        out = out + self.shortcut(x)
        return out


class PreActBottleneck(nn.Module):
    '''Pre-activation version of the original Bottleneck module.'''
    expansion = 4

    def __init__(self, in_channels, out_channels, stride, dropout, neuron: callable = None, **kwargs):
        super(PreActBottleneck, self).__init__()
        whether_bias = True

        self.bn1 = nn.BatchNorm2d(in_channels)

        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride, padding=0, bias=whether_bias)
        self.bn2 = nn.BatchNorm2d(out_channels)

        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=whether_bias)
        self.bn3 = nn.BatchNorm2d(out_channels)
        self.dropout = layer.Dropout(dropout)
        self.conv3 = nn.Conv2d(out_channels, self.expansion * out_channels, kernel_size=1, stride=1, padding=0, bias=whether_bias)

        if stride != 1 or in_channels != self.expansion * out_channels:
            self.shortcut = nn.Conv2d(in_channels, self.expansion * out_channels, kernel_size=1, stride=stride, padding=0, bias=whether_bias)
        else:
            self.shortcut = nn.Sequential()

        self.relu1 = neuron(**kwargs)
        self.relu2 = neuron(**kwargs)
        self.relu3 = neuron(**kwargs)

    def forward(self, x):
        x = self.relu1(self.bn1(x))

        out = self.conv1(x)
        out = self.conv2(self.relu2(self.bn2(out)))
        out = self.conv3(self.dropout(self.relu3(self.bn3(out))))

        out = out + self.shortcut(x)

        return out


class PreActResNet(nn.Module):

    def __init__(self, block, num_blocks, num_classes, dropout, neuron: callable = None, **kwargs):
        super(PreActResNet, self).__init__()
        self.num_blocks = num_blocks

        self.data_channels = kwargs.get('c_in', 3)
        self.init_channels = 64
        self.conv1 = nn.Conv2d(self.data_channels, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.layer1 = self._make_layer(block, 64, num_blocks[0], 1, dropout, neuron, **kwargs)
        self.layer2 = self._make_layer(block, 128, num_blocks[1], 2, dropout, neuron, **kwargs)
        self.layer3 = self._make_layer(block, 256, num_blocks[2], 2, dropout, neuron, **kwargs)
        self.layer4 = self._make_layer(block, 512, num_blocks[3], 2, dropout, neuron, **kwargs)

        self.bn1 = nn.BatchNorm2d(512 * block.expansion)
        self.pool = nn.AvgPool2d(4)
        self.flat = nn.Flatten()
        self.drop = layer.Dropout(dropout)
        self.linear = nn.Linear(512 * block.expansion, num_classes)

        self.relu1 = neuron(**kwargs)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, val=1)
                nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Linear):
                nn.init.zeros_(m.bias)

    def _make_layer(self, block, out_channels, num_blocks, stride, dropout, neuron, **kwargs):
        strides = [stride] + [1] * (num_blocks-1)
        layers = []
        for stride in strides:
            layers.append(block(self.init_channels, out_channels, stride, dropout, neuron, **kwargs))
            self.init_channels = out_channels * block.expansion
        return nn.Sequential(*layers)

    def forward(self, x):
        out = self.conv1(x)
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = self.pool(self.relu1(self.bn1(out)))
        out = self.drop(self.flat(out))
        out = self.linear(out)
        return out


class TestNet_3(nn.Module):

    def __init__(self, num_classes, dropout, neuron: callable = None, **kwargs):
        super(TestNet_3, self).__init__()

        self.data_channels = kwargs.get('c_in', 3)

        self.conv1 = nn.Conv2d(self.data_channels, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu1 = neuron(**kwargs)

        self.conv2 = nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(128)
        self.relu2 = neuron(**kwargs)


        self.pool = nn.AvgPool2d(4)
        self.flat = nn.Flatten()
        self.drop = layer.Dropout(dropout)
        self.linear = nn.Linear(512 * 4, num_classes)



        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, val=1)
                nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Linear):
                nn.init.zeros_(m.bias)


    def forward(self, x):
        out = self.relu1(self.bn1(self.conv1(x)))
        out = self.relu2(self.bn2(self.conv2(out)))

        out = self.pool(out)
        out = self.drop(self.flat(out))
        out = self.linear(out)
        return out




class TestNet_5(nn.Module):

    def __init__(self, num_classes, dropout, neuron: callable = None, **kwargs):
        super(TestNet_5, self).__init__()

        self.data_channels = kwargs.get('c_in', 3)

        self.conv1 = nn.Conv2d(self.data_channels, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu1 = neuron(**kwargs)

        self.conv2 = nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(128)
        self.relu2 = neuron(**kwargs)

        self.conv3 = nn.Conv2d(128, 256, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn3 = nn.BatchNorm2d(256)
        self.relu3 = neuron(**kwargs)

        self.conv4 = nn.Conv2d(256, 512, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn4 = nn.BatchNorm2d(512)
        self.relu4 = neuron(**kwargs)


        self.pool = nn.AvgPool2d(4)
        self.flat = nn.Flatten()
        self.drop = layer.Dropout(dropout)
        self.linear = nn.Linear(512, num_classes)



        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, val=1)
                nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Linear):
                nn.init.zeros_(m.bias)


    def forward(self, x):
        out = self.relu1(self.bn1(self.conv1(x)))
        out = self.relu2(self.bn2(self.conv2(out)))
        out = self.relu3(self.bn3(self.conv3(out)))
        out = self.relu4(self.bn4(self.conv4(out)))
        out = self.pool(out)
        out = self.drop(self.flat(out))
        out = self.linear(out)
        return out



class TestNet_9(nn.Module):

    def __init__(self, num_classes, dropout, neuron: callable = None, **kwargs):
        super(TestNet_9, self).__init__()

        self.data_channels = kwargs.get('c_in', 3)

        self.conv1 = nn.Conv2d(self.data_channels, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu1 = neuron(**kwargs)

        self.conv11 = nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn11 = nn.BatchNorm2d(64)
        self.relu11 = neuron(**kwargs)

        self.conv2 = nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(128)
        self.relu2 = neuron(**kwargs)

        self.conv22 = nn.Conv2d(128, 128, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn22 = nn.BatchNorm2d(128)
        self.relu22 = neuron(**kwargs)

        self.conv3 = nn.Conv2d(128, 256, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn3 = nn.BatchNorm2d(256)
        self.relu3 = neuron(**kwargs)

        self.conv33 = nn.Conv2d(256, 256, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn33 = nn.BatchNorm2d(256)
        self.relu33 = neuron(**kwargs)

        self.conv4 = nn.Conv2d(256, 512, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn4 = nn.BatchNorm2d(512)
        self.relu4 = neuron(**kwargs)

        self.conv44 = nn.Conv2d(512, 512, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn44 = nn.BatchNorm2d(512)
        self.relu44 = neuron(**kwargs)


        self.pool = nn.AvgPool2d(4)
        self.flat = nn.Flatten()
        self.drop = layer.Dropout(dropout)
        self.linear = nn.Linear(512, num_classes)



        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, val=1)
                nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Linear):
                nn.init.zeros_(m.bias)


    def forward(self, x):
        out = self.relu1(self.bn1(self.conv1(x)))
        out = self.relu11(self.bn11(self.conv11(out)))
        out = self.relu2(self.bn2(self.conv2(out)))
        out = self.relu22(self.bn22(self.conv22(out)))
        out = self.relu3(self.bn3(self.conv3(out)))
        out = self.relu33(self.bn33(self.conv33(out)))
        out = self.relu4(self.bn4(self.conv4(out)))
        out = self.relu44(self.bn44(self.conv44(out)))
        out = self.pool(out)
        out = self.drop(self.flat(out))
        out = self.linear(out)
        return out


def res18(neuron: callable = None, num_classes=10,  neuron_dropout=0, **kwargs):
    return PreActResNet(PreActBlock, [2, 2, 2, 2], num_classes, neuron_dropout, neuron=neuron, **kwargs)


def res34(neuron: callable = None, num_classes=10,  neuron_dropout=0, **kwargs):
    return PreActResNet(PreActBlock, [3, 4, 6, 3], num_classes, neuron_dropout, neuron=neuron, **kwargs)

def spiking_testnet_3(neuron: callable = None, num_classes=10,  neuron_dropout=0, **kwargs):
    return TestNet_3(num_classes, neuron_dropout, neuron=neuron, **kwargs)

def spiking_testnet_5(neuron: callable = None, num_classes=10,  neuron_dropout=0, **kwargs):
    return TestNet_5(num_classes, neuron_dropout, neuron=neuron, **kwargs)

def spiking_testnet_9(neuron: callable = None, num_classes=10,  neuron_dropout=0, **kwargs):
    return TestNet_9(num_classes, neuron_dropout, neuron=neuron, **kwargs)
