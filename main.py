from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from typing import Optional
from sqlalchemy.orm import Session
# 데이터를 담는 그릇의 역활 -> DTO 구성
from pydantic import BaseModel
# ---------------------------------------------------------------------------------------------------------
#
#   전역변수 : 앱, 템플릿, 정적폴더, ORM 설정
# 
# ---------------------------------------------------------------------------------------------------------
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


# 테이블 구성 -> 고객 관련 마스터 테이블 클래스
class User(BaseTableModel):
    __tablename__ = "users"
    id                 = Column(Integer, primary_key=True, index=True)
    username           = Column(String(128), unique=True, index=True)
    email              = Column(String(256))
    hashed_password    = Column(String(512))

# 회원가입시 데이터를 담을 그릇 -> DTO
class UserInsert(BaseModel): 
    username : str
    email    : str
    password : str # 가입할때는 암호화 하기 전 비밀번호다/ 고객이 입력할때 암호화하고 기억하진 않으니까

# 로그인할 때 데이터를 담을 그릇 -> DTO
class UserLogin(BaseModel): 
    username : str
    password : str # 가입할때는 암호화 하기 전 비밀번호다/ 고객이 입력할때 암호화하고 기억하진 않으니까

# 테이블 구성 -> 메모 관련 마스터 테이블 클레스
# BaseTableModel을 상속받음으로써 ORM 모델 되고->테이블 구성하게 됨 : 규칙
class Memo(BaseTableModel):
    __tablename__ = 'memo'   # 테이블명 -> Memo객체는 memo 테이블과 연결됨
    # 컬럼 구성
    id      = Column(Integer, primary_key=True, index=True) # index 검색
    title   = Column(String(128))
    content = Column(String(2048)) # varchar(2048)

# 메모 작성용(create or insert) 클레스
# 사용자가 작성한 데이터를 본 객체에 담아서 -> .. -> 디비에 반영
# MemoInsert => 데이터를 담는 그릇 => DTO(자바 진영의 표현)
# DTO(Data Transfer Object, 데이터 전송 객체)란 프로세스 간에 데이터를 전달하는 객체
class MemoInsert(BaseModel):
    title : str
    content : str

# 메모 수정용 클레스
# 테이블 구조상 Null 허용하게 구성되어 있으므로
# Optional[str] 이용하여 결측(null or  None)도 가능 실제 값도 가능
class MemoUpdate(BaseModel):
    title : Optional[str]   = None
    content : Optional[str] = None

# 메모 조회 -> 추후
# 메모 삭제 -> 추후

# 디비 커넥션 획득 혹은 반납에 관련된 함수
def get_connection():
    '''
     - 각 API(메모 등록/수정/조회/삭제..) 호출시 독립적으로 DB관련 세션(연결)을 제공
     - 세션을 제공!!을 받음 -> API에게 전달
     - API가 사용 -> 딜레이 -> 사용종료 -> 세션을 반납!!
     - 제너레이터 기법을 이용하여 위의 방식을 동기식으로 코드 처리함 => yield
    '''
    db_session = Session(bind=engine) # 디비 세션 생성(풀에서 빌림) -> I/O
    try:
        yield db_session # API에서 세션을 전달하는 행위
        # yield를 사용해서 이 함수가 바로 종료되지 않고, 대기함 
        # -> API가 사용 마무리 할때까지
    except Exception as e:
        print('디비 세션 획득 오류', e)
    finally:
        if db_session:
            # (커넥션) 풀에 연결 세션을 반납하는 행위
            db_session.close()


# BaseTableModel을 상속받은 모든 모델을 찾아라 
# -> 데이터베이스와 연결 확인(연결 진행) -> 테이블 체크 -> 없으면 생성함.
BaseTableModel.metadata.create_all(bind=engine)






# ---------------------------------------------------------------------------------------------------------
#
#   라우팅
# 
# ---------------------------------------------------------------------------------------------------------
@app.get("/")
def home(req : Request,
         db_conn : Session = Depends(get_connection)
         ):
    # html 읽어서 -> 필요한 데이터를 전달하여 -> 데이터 이용하여 동적으로 html 구성
    # -> html을 응답 => TemplateResponse
    memos = db_conn.query(Memo).all() # 모든 메모 가져오기
    return templates.TemplateResponse('memo.html', {
        "request": req,
        "memos"  : memos
    })

# restful 방식으로 URL 설계중 -> CRUD -> 기능만 구현중!!(화면 x) -> API 구현중
# 메모 신규 생성
# 로그인및 사용자 인증 정보 x
# post 방식 : 대량의 텍스트 전송 필요
# Depends(get_connection) : 
# -> 디비 커넥션 풀을 통해서 관리하고 잇는 커넥션 1개를 빌려옴. 의존성주입:DI(차후에 이해)
@app.post("/memo/")
async def create_memo(memo : MemoInsert, 
                   db_conn : Session = Depends(get_connection)):
    '''
    - 입력 ( parameters )
        - memo    : 테이블에 추가할 메모 데이터(제목,내용) => DTO => MemoInsert
        - db_conn : 해당 메모를 데이터베이스에 삽입 => 디비 커넥션(세션) 1개 획득(빌림)
    - 처리
        - 메모 데이터를 이용하여 Memo 클레스기반 객체 1개 생성
        - db_conn을 이용하여 데이터베이스에 추가
        - db_conn을 이용하여 커밋처리
        - db_conn을 이용하여 이용하여 새로고침 처리
    - 출력
        - 결과 반환(필요시 정보 추가)
    '''
    #### 처리 ####    
    # 사전 처리된 내용 기술
    # 사용자 데이터 입력 -> 요청(데이터전송) -> pydantic MemoInsert의해
    # -> 유효성검사 후 MemoInsert에 담김(객체 생성) 
    
    # 메모 데이터를 이용하여 Memo 클레스(DB에 연결된)기반 객체 1개 생성
    # -> Memo 객체 생성(데이터 인자로 전달)
    memo = Memo(title=memo.title, content=memo.content)

    # db_conn을 이용하여 데이터베이스에 추가
    db_conn.add( memo ) # insert into ~ 

    # db_conn을 이용하여 커밋(디비에 실제 반영됨)처리
    db_conn.commit()

    # db_conn을 이용하여 이용하여 새로고침 처리 -> id값을 획득하는 과정
    db_conn.refresh( memo )

    # 반환(출력) -> dict 구조로 디비에 저장된 내용(정보)를 반환 (컨셉)
    return { 
        "id"    : memo.id, 
        "title" : memo.title,
        "content" : memo.content
    }

# 메모 조회 -> 최대로 가봐야 페이지번호 -> get
# 모든 메모 조회 (select * from memo;)하는 API
@app.get("/memo/")
async def select_memo(db_conn : Session = Depends(get_connection)):
    # query(Memo) : memo 테이블에 결과물(셋)은  Memo 클레스에 담겠다
    # all() : select * from memo; 이 쿼리를 수행하여 
    #         Memo 객체를 리스트로 담아서 반환
    return db_conn.query(Memo).all()
    pass

# 메모 수정 -> 조건식 필요 -> 메모를 특정할수 있는 (고유)값필요
# 경로 매개변수를 통해서 메모 데이터의 고유한 ID를 전달 -> 일반적 디자인
@app.put("/memo/{memo_id}")
async def select_memo(memo_id : int, memo : MemoUpdate, 
                      db_conn : Session = Depends(get_connection)):
    # 1. 수정하고자 하는 메모 획득 (id가 일치하는 모든 메모중 첫번째것 획득)
    target_memo = db_conn.query(Memo).filter(Memo.id == memo_id).first()
    if not target_memo:
        return { "type":"error", "msg":"발견된 메모가 없습니다." }
    
    # 2. 수정하고자 하는 내용이 있는 컬럼만 대체 (수정된것만 보낼수 있음)
    if memo.title:
        target_memo.title = memo.title      # 제목 대체
    if memo.content:
        target_memo.content = memo.content  # 내용 대체        

    # 3. 커밋
    db_conn.commit()

    # 4. 메모 갱신
    db_conn.refresh( target_memo )

    # 5. 응답 -> 바뀐 내용기반으로 메모 정보를 출력
    return { "type":"success", "data":{
        "id"        : target_memo.id,
        "title"     : target_memo.title,
        "content"   : target_memo.content
    } }

# 메모 삭제 -> 조건식 필요-> 메모를 특정할수 있는 (고유)값필요
# 경로 매개변수를 통해서 메모 데이터의 고유한 ID를 전달 -> 일반적 디자인
@app.delete("/memo/{memo_id}")
async def delete_memo(memo_id : int, 
                      db_conn : Session = Depends(get_connection)
                     ):
    # 1. 해당 ID에 일치하는(where ~ ) 데이터중 첫번째것 획득
    # 모든 데이터를 하나씩 꺼내서 Memo 객체에 담고 -> 비교 
    # -> 일치하는것만 모아서 -> 첫번째것만 추출
    target_memo = db_conn.query(Memo).filter(Memo.id == memo_id).first()

    # 2. 1번의 결과물이 없다면, 해당 메모는 없다(이미 삭제됨)는 메세지 처
    if not target_memo:
        return { "type":"error", "msg":"발견된 메모가 없습니다." }

    # 3. 메모가 있다면 -> 삭제
    db_conn.delete( target_memo ) # delete ~ 

    # 4. 커밋
    db_conn.commit()

    # 5. 응답 -> 삭제 성공 메세지 전송
    return { "type":"success", "msg":"메모가 삭제되었습니다." }
