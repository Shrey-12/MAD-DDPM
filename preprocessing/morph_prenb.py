
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from retinaface import RetinaFace
import cv2
import os

class CustomWideResNet(nn.Module):
    def __init__(self):
        super(CustomWideResNet, self).__init__()
        self.wide_resnet = models.wide_resnet50_2(pretrained=True)
        # Remove the final fully connected layer
        self.wide_resnet = nn.Sequential(*list(self.wide_resnet.children())[:-1])
        # Add a custom fully connected layer with 1024 channels and appropriate spatial dimensions
        self.custom_fc = nn.Linear(2048, 1024 * 14 * 14)

    def forward(self, x):
        x = self.wide_resnet(x)
        x = self.custom_fc(x.view(x.size(0), -1))
        x = x.view(x.size(0), 1024, 14, 14)
        return x

# Load the Wide ResNet 50 model, ensuring correct model name
model = CustomWideResNet()
ccount = 0

image_paths =[]

morphs_dir = "data/FRLL/images/morphs/"
for method_folder_name in os.listdir(morphs_dir):
    method_folder_path = os.path.join(morphs_dir,method_folder_name)
    if os.path.isdir(method_folder_path):
        for filename in os.listdir(method_folder_path):
            if filename.endswith('.jpg'):
                image_paths.append([method_folder_name,os.path.join(method_folder_path,filename)])

def load_and_preprocess(img_path, scale):
    # Load image
    global ccount
    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Assuming RetinaFace is used for face detection
    faces = RetinaFace.detect_faces(img)
    if len(faces) > 0:
        # Assuming you want to use the first detected face
        face_info = faces['face_1']

        # Extract the bounding box information
        score = face_info['score']
        facial_area = face_info['facial_area']
        left, top, right, bottom = facial_area

        # Crop the face with a margin of 5% of the detected bounding box height
        margin = int(0.05 * (bottom - top))
        cropped_face = img[max(0, top - margin):bottom + margin, max(0, left - margin):right + margin]

        # Resize the image to the desired scale
        size = (224, 224) if scale == 1 else (448, 448)
        normalized_img = transforms.ToTensor()(cv2.resize(cropped_face, size))
        print(normalized_img.shape)
        if scale==1:
            features = model(normalized_img.unsqueeze(0))

            features_squeezed = features.squeeze(0)
            return features_squeezed

        if scale==2:
            kernel_size, stride = 224, 224
            patches = normalized_img.unfold(2, kernel_size, stride).unfold(1, kernel_size, stride)
            patches = patches.contiguous().view(-1, 3, kernel_size, kernel_size)
            print(patches.shape)
            features = []
            for patch in patches:
                patch_features = model(patch.unsqueeze(0))
                features.append(patch_features.squeeze(0))
            combined_features = torch.stack(features, dim=0)
            return combined_features
    else:
        print(f"No faces detected in {img_path}")
        ccount-=1
        return None

for method_name,img_path in image_paths:
    ccount+=1
    image_name = os.path.basename(img_path)
    for scale in [1, 2]:
        feature_path = f"data/FRLL/features_scale_{scale}/morphs/{method_name}/{image_name.replace('.jpg', '.pt')}"
        if os.path.exists(feature_path):
            print("repeated: ",ccount)
            continue
        else:
            sqfeat= load_and_preprocess(img_path, scale)
            # print(normalized_img.shape)
            if sqfeat is not None:
                pass
                # print(features_squeezed.shape)
                # model, dir
                torch.save(sqfeat, feature_path)

print("Number of pt generated: ",ccount)
