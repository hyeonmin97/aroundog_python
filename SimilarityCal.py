import pandas as pd
import pymysql

from rdp import rdp
import similaritymeasures
import folium
import webbrowser
from hashlib import md5

import requests
import json
from tqdm import tqdm
import time
import threading
import time


class SimilarityCal(threading.Thread):

    def getGeocoding(self, coor):
        # coor = longitude, latitude
        path = "https://naveropenapi.apigw.ntruss.com/map-reversegeocode/v2/gc?coords=" + coor + "&orders=admcode&output=json"
        headers = {"X-NCP-APIGW-API-KEY-ID": "atguginznv",
                   "X-NCP-APIGW-API-KEY": "Ts1fkNKJB08RiFOrZrzQSdigNXhasXLcbM5wmlTV"}
        response = requests.get(path, headers=headers).text
        a = json.loads(response)

        area1 = a["results"][0]["region"]["area1"]["name"]
        area2 = a["results"][0]["region"]["area2"]["name"]
        area3 = a["results"][0]["region"]["area3"]["name"]
        area4 = a["results"][0]["region"]["area4"]["name"]

        return area1 + " " + area2 + " " + area3 + " " + area4

    def auto_open(self, m, path):
        html_page = f'{path}'
        m.save(html_page)
        # open in browser.
        new = 2
        webbrowser.open(html_page, new=new)

    # row 생략 없이 출력
    # pd.set_option('display.max_rows', None)
    # col 생략 없이 출력
    # pd.set_option('display.max_columns', None)

    def connDB(self):
        host_name = 'localhost'
        host_port = 3306
        username = 'dev'
        password = 'dev'
        database_name = 'aroundog'

        db = pymysql.connect(
            host=host_name,  # MySQL Server Address
            port=host_port,  # MySQL Server Port
            user=username,  # MySQL username
            passwd=password,  # password for MySQL username
            db=database_name,  # Database name
            charset='utf8'
        )
        return db

    # walkHash 테이블 생성
    # id : 자동생성
    # rdp : rdp 적용된 경로
    # hash : 해시 코드 값(id)
    #
    # 1. 새로운 값 rdp 적용
    # 2. walkHash 테이블의  데이터들과 비교해서 최종적으로 중복이 아니면 walkHash에 추가
    #     / 중복일 경우 walk 테이블 hash 컬럼에 해시값 저장
    #
    def getWalkDeduplication(self):
        try:
            db = self.connDB()
            with db.cursor() as curs:
                sql = "select * from walk_deduplication"
                deduplicationTable = pd.read_sql(sql, db)
                deduplicationList = []
                # 데이터 형식 변경
                for index, row in tqdm(deduplicationTable.iterrows(), total=deduplicationTable.shape[0]):
                    tempDf = pd.read_json(row['rdp'])  # [] 제거
                    rdpData = rdp(tempDf, epsilon=0.000001)
                    deduplicationId = row['id']
                    hashCode = row["hash"]
                    img = row["img"]
                    tile = row["tile"]
                    second = row['second']
                    distance = row['distance']
                    address = row['address']
                    deduplicationList.append(
                        {"id": deduplicationId, "rdp": rdpData, "hash": hashCode, "img": img, "tile": tile,
                         "second": second,
                         "distance": distance, "address": address})
        finally:
            db.close()
            return deduplicationList

    def getWalk(self):
        try:
            db = self.connDB()
            with db.cursor() as curs:
                sql = "select * from walk where hash is null"
                walkTable = pd.read_sql(sql, db)
        finally:
            db.close()
            return walkTable

    def run(self):
        while True:
            walkTable = self.getWalk()
            if not walkTable.empty:
                deduplicationList = self.getWalkDeduplication()
                try:
                    db = self.connDB()
                    with db.cursor() as curs:
                        # newDeduplicated = []
                        # 데이터 형식 변경
                        for index, row in tqdm(walkTable.iterrows(), total=walkTable.shape[0]):
                            tempDf = pd.read_json(row['course'][1:-1])  # [] 제거
                            walkRdp = rdp(tempDf, epsilon=0.000001)
                            # walk 데이터
                            walkId = row['id']
                            img = row['img']
                            tile = row['tile']
                            second = row['second']
                            distance = row['distance']
                            # rdpList.append(
                            #     {"id": walkId, "rdp": walkRdp, "img": img, "tile": tile})

                            isDuplicated = False
                            # 산책 기록과 대표 산책 기록 전체 비교
                            for deduplication in deduplicationList:
                                deduplicateRdp = deduplication["rdp"]
                                hashCode = deduplication["hash"]
                                df = similaritymeasures.frechet_dist(walkRdp, deduplicateRdp)
                                dtw, d = similaritymeasures.dtw(walkRdp, deduplicateRdp)

                                # 중복일 때
                                if df < 0.003 and dtw < 0.3:
                                    # walk 에 hash 코드 추가
                                    sql = "update walk set hash = %s where id = %s"
                                    curs.execute(sql, (hashCode, walkId))
                                    db.commit()
                                    isDuplicated = True
                                    break

                            # 중복 아닐때
                            if not isDuplicated:
                                hashCode = md5(str(walkId).encode('utf-8')).hexdigest()
                                # newDeduplicated.append(hashCode)
                                coor = str(walkRdp[0][1]) + "," + str(walkRdp[0][0])
                                address = self.getGeocoding(coor)
                                # 중복 없는 테이블에 값 추가(대표 산책 추가)
                                sql1 = "insert into walk_deduplication(rdp, hash, img, tile, second, distance, address) " \
                                       "values(%s, %s, %s, %s, %s, %s, %s)"
                                curs.execute(sql1, (str(walkRdp), hashCode, img, tile, second, distance, address))
                                deduplicationId = curs.lastrowid  # 방금 추가된 id 저장

                                # 산책 테이블에 해시값 추가
                                sql2 = "update walk set hash = %s where id = %s"
                                curs.execute(sql2, (hashCode, walkId))
                                db.commit()

                                # 중복 테이블값을 가지고있는 리스트에 추가
                                deduplicationList.append(
                                    {"id": deduplicationId, "rdp": walkRdp, "hash": hashCode, "img": img, "tile": tile,
                                     "second": second, "distance": distance, "address": address})

                finally:
                    db.close()
            else:
                print("no new walk data")
            print("thread sleep")
            time.sleep(5)
#
# print("deduplicationList : ", deduplicationList)
# for deduplication in deduplicationList:
#     m = folium.Map(location=[37.66298165, 127.06460064999999], zoom_start=30)
#     for coor in deduplication['rdp']:
#         loc = tuple(coor)
#         folium.CircleMarker(
#             location=loc,
#             radius=2,
#             fill='blue'
#         ).add_to(m)
#     auto_open(m, str(deduplication['id']) + ".html")


# rev = pd.read_json(walkTable.iloc[-1]['course'][1:-1])
# rev = rev[::-1]
# revD = rdp(rev, epsilon=0.000001)
#
#
# def test(x, y):
#     df = similaritymeasures.frechet_dist(rdpList[x]['rdp'], rdpList[y]['rdp'])
#     dtw, d = similaritymeasures.dtw(rdpList[x]['rdp'], rdpList[y]['rdp'])
#     print("df :", df)
#     print("dtw: ", dtw)
#     # print(df)
#     for i in range(0, len(rdpList[x]['rdp'])):
#         loc = tuple(rdpList[x]['rdp'][i])
#         folium.CircleMarker(
#             location=loc,
#             radius=2,
#             fill='blue'
#         ).add_to(m)
#     auto_open("file.html")
#
#     for i in range(0, len(rdpList[y]['rdp'])):
#         loc = tuple(rdpList[y]['rdp'][i])
#         folium.CircleMarker(
#             location=loc,
#             radius=2,
#             fill=True,
#             color='red'
#         ).add_to(m)
#     auto_open("file2.html")
