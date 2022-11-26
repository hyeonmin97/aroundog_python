aroundog_python
============ 
[aroundog](https://github.com/qqqqlss/arounDog)에서 사용하는 산책로의 중복을 제거하는 코드 
<br><br>

## 특징
- 더글라스-패커 알고리즘을 통해 산책 경로의 정점 수를 줄임
- 프레셔 거리와 동적 시간 와핑을 통해 산책경로 유사도 판별
- 네이버 지도 API를 호출해 좌표의 법정동 저장
<br><br>

## 사용한 라이브러리

|라이브러리|설명
|----|-------------------|
|pymysql|MySQL 연결
|pandas|DB의 테이블 내용 다룰 때 사용
|requests|좌표로 법정동 지소를 얻기 위해 네이버 API를 호출하기 위한 HTTP 통신 라이브러리
|json|json 파싱에 사용되는 라이브러리|
|tqdm|진행도를 보여주는 라이브러리|
|hashlib|해시 코드를 만들기 위한 라이브러리|
|similaritymeasures|그래프 유사도 판별 라이브러리|
|rdp|Ramer-Douglas-Peucker 알고리즘|
