from sqlalchemy import create_engine,Column,Integer,String,Boolean
from sqlalchemy.orm import declarative_base,sessionmaker

#1.配置数据库连接 URL(对应刚才启动的Docker 启动的参数)
SQLALCHEMY_DATABASE_URL = "postgresql://admin:123456@localhost:5432/smart_home"

#2.创建数据库引擎
engine = create_engine(SQLALCHEMY_DATABASE_URL)

#3.创建会话工厂，用于后续在API中操作数据库
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#4.声明基类，所有的ORM模型类都将继承这个基类
Base = declarative_base()

#5.定义Device 模型（对应数据库里的 devices 表）
class DBDevice(Base):
    __tablename__ = "devices"

    device_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True,nullable=False)
    room = Column(String, nullable=False)
    is_on = Column(Boolean, default=False,nullable=False)