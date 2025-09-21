import cv2

cap = cv2.VideoCapture(0)
ret, frame = cap.read()
if ret:
    cv2.imshow("Test", frame)
    cv2.waitKey(0)
cap.release()
cv2.destroyAllWindows()
