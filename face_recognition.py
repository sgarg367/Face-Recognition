# -*- coding: utf-8 -*-
import face_recognition
from multiprocessing.dummy import Pool
import cv2
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import glob
import win32com.client as wincl

PADDING = 50
ready_to_detect_identity = True
windows10_voice_interface = wincl.Dispatch("SAPI.SpVoice")



def prepare_database():
    database = {}

    # load all the images of individuals to recognize into the database
    for file in glob.glob("images/*"):
        identity = os.path.splitext(os.path.basename(file))[0]
        img = face_recognition.load_image_file(file)
        database[identity] = face_recognition.face_encodings(img)[0]

    return database

def process_frame(img, frame, face_cascade):
    """
    Determine whether the current frame contains the faces of people from our database
    """
    global ready_to_detect_identity
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    # Loop through all the faces detected and determine whether or not they are in the database
    identities = []
    for (x, y, w, h) in faces:
        x1 = x-PADDING
        y1 = y-PADDING
        x2 = x+w+PADDING
        y2 = y+h+PADDING

        img = cv2.rectangle(frame,(x1, y1),(x2, y2),(255,0,0),2)

        identity = find_identity(frame, x1, y1, x2, y2,img)

        if identity is not None:
            cv2.putText(img, "Face : " + identity, (x-50, y-50), cv2.FONT_HERSHEY_PLAIN, 1.5, (0, 255, 0), 2)
            identities.append(identity)

    if identities != []:
        cv2.imwrite('example.png',img)

        ready_to_detect_identity = False
        pool = Pool(processes=1) 
        # We run this as a separate process so that the camera feedback does not freeze
        pool.apply_async(welcome_users, [identities])
    return img

def find_identity(frame, x1, y1, x2, y2,img):
   
    height, width, channels = frame.shape
    # The padding is necessary since the OpenCV face detector creates the bounding box around the face and not the head
    part_image = frame[max(0, y1):min(height, y2), max(0, x1):min(width, x2)]
    
    return who_is_it(part_image, database)

def who_is_it(image, database):
    """ 
    Arguments:
    database -- database containing image encodings along with the name of the person on the image
    image -- image detected in the video
    Returns:
    identity -- string, the name prediction for the person on image_path
    """
    
    encodings = face_recognition.face_encodings(image)
    if len(encodings) > 0:
        encoding = encodings[0]
    else:
        print("No faces found in the image!")
        return None
        
    identity = None
    
    # Loop over the database dictionary's names and encodings.
    for (name, db_enc) in database.items():
        
        result = face_recognition.compare_faces([db_enc], encoding)
       # print('%s -> %s' %(name,result))
        identity = name
        if result[0] == True:
            return str(identity)
    if result[0] == False:
        return None
        
		
def webcam_face_recognizer(database):
    """
    Runs a loop that extracts images from the computer's webcam and determines whether or not
    it contains the face of a person in our database.

    If it contains a face, an audio message will be played targetting the user.
    If not, the program will process the next frame from the webcam
    """
    global ready_to_detect_identity

    cv2.namedWindow("preview")
    vc = cv2.VideoCapture(0)

    face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
    
    while vc.isOpened():
        _, frame = vc.read()
        img = frame

        # We do not want to detect a new identity while the program is in the process of identifying another person
        if ready_to_detect_identity:
            img = process_frame(img, frame, face_cascade)   
        
        key = cv2.waitKey(10)
        cv2.imshow("preview", img)

        if key == 27: # exit on ESC
            break
    cv2.destroyWindow("preview")

def welcome_users(identities):
    """ Outputs a audio message to the users """
    global ready_to_detect_identity
    welcome_message = 'hi, '

    if len(identities) == 1:
        welcome_message += '%s, is found.' % identities[0]
    else:
        for identity_id in range(len(identities) - 1):
            welcome_message += '%s, ' % identities[identity_id]
        welcome_message += 'and %s, ' % identities[-1]
        welcome_message += 'are found!'

    windows10_voice_interface.Speak(welcome_message)

    # Allow the program to start detecting identities again
    ready_to_detect_identity = True

if __name__ == "__main__":
    database = prepare_database()
    webcam_face_recognizer(database)


