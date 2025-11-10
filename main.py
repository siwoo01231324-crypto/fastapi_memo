from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static",StaticFiles(directory="static"),name="static")

# ORM 작업 (전역 변수 위치)
# 데이터베이스 연동 URL 구성 = 프로토콜://아이디:비밀번호@IP/데이터베이스명
DATABASE_URL = "mysql+pymysql://root:1234@127.0.0.1/memos"
# 데이터베이스에 실제 연결을 담당할 엔진
engine      = create_engine( DATABASE_URL )
# 테이블 구성에 필요한 재료 준비 -> 모든 ORM 모델들이 상속받아야 할 클레스 구성
BaseTableModel = declarative_base()

# 테이블 구성 -> 메모 관련 마스터 테이블 클레스
# BaseTableModel을 상속받음으로써 ORM 모델 되고->테이블 구성하게 됨 : 규칙
class Memo(BaseTableModel):
    __tablename__ = 'memo'   # 테이블명 -> Memo객체는 memo 테이블과 연결됨
    # 컬럼 구성
    id      = Column(Integer, primary_key=True, index=True) # index 검색
    title   = Column(String(128))
    content = Column(String(2048)) # varchar(2048)

# BaseTableModel을 상속받은 모든 모델을 찾아라 
# -> 데이터베이스와 연결 확인(연결 진행) -> 테이블 체크 -> 없으면 생성함.
BaseTableModel.metadata.create_all(bind=engine)


@app.get("/")
def home(req : Request):
    return { "title":"메모 서비스" }