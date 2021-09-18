"""
Developer: Umut Ucok

Need:
Make long time async gp request before/after edit on any layer and save the result into somewhere (in db),
see: create_request_pool.sql

Workflow:
1- Create a table: process_pool. Add columns like "created_date", "finished_date", "service_url" "params", "status" etc.

2- Write an SQL trigger or use arcade to insert new request record whenever edited X layer.

3- You have to develop and run something, unfortunately. Check my Python solution. Uses 2 thread class.
One for refreshing pool via requesting your "process_pool" table and other is for request.


References:
    https://developers.arcgis.com/python/api-reference/arcgis.geoprocessing.html
"""

from asyncio.futures import Future
from datetime import datetime
from threading import Thread

from arcgis.geoprocessing import import_toolbox
from arcgis.gis import GIS
from sqlalchemy import create_engine

db_username = ""
db_password = ""
db_hostname = ""
db_port = 1521  # oracle default port change whatever yours use
db_service_name = ""  # only for oracle. see sqlalchemy connection string for others


db = create_engine(f'oracle+cx_oracle://{db_username}:{db_password}@{db_hostname}:{db_port}/?service_name={db_service_name}')
portal = ""  # your arcgis portal link. you can type arcgis.com if you use online
usr = ""  # agol user
pwd = ""  # agol pwd
tool = "https://localhost/server/rest/services/test/MyToolbox/GPServer"  # change it yours

my_gisportal = GIS(portal, usr, pwd, verify_cert=False)
tbx = import_toolbox(tool, gis=my_gisportal)


class PoolRefresher(Thread):
    """
    This is our main thread in fact. It queries the SDE.REQUEST_POOL (change it if stored in another place)
    always and create task if there is WAITING status

    database connection object stored in here also so that all db operations handled here
    """
    _sql = "select service_name, service_url, params, status " \
           "from SDE.REQUEST_POOL where status = 'WAITING'"
    connection = db.connect()
    fut = Future()

    @classmethod
    def finish_task(cls, service_name):
        update_sql = f"UPDATE SDE.REQUEST_POOL set status = 'FINISHED' WHERE service_name = '{service_name}'"
        cls.connection.execute(update_sql)
        print("task set finished in db")

    @classmethod
    def run_task(cls, service_name):
        update_sql = f"UPDATE SDE.REQUEST_POOL set status = 'RUNNING' WHERE service_name = '{service_name}'"
        cls.connection.execute(update_sql)
        print("task set run in db")

    @classmethod
    def get_service_status(cls, service_name):
        _sql = f"SELECT status FROM SDE.REQUEST_POOL WHERE service_name = '{service_name}'"
        return cls.connection.execute(_sql).fetchall()

    @classmethod
    def get_waiting_services(cls):
        return cls.connection.execute(cls._sql).fetchall()

    @classmethod
    def get_running_services(cls):
        _sql = cls._sql.replace('WAITING', 'RUNNING')
        return cls.connection.execute(_sql).fetchall()

    def run(self):
        print("Pool refresher is up and running")
        while True:
            for row in self.connection.execute(self._sql):
                # creation
                print("Task creating")
                task = GPRequest(*row)
                task.start()


class GPRequest(Thread):
    """
    A class only represents service request operation
    """
    def __init__(self, service_name, service_url, params, status):
        # service info
        self.service_name = service_name
        self.service_url = service_url
        self.params = params
        self.status = status

        # time info
        self.created_date = datetime.now()
        self.finished_date = None

        super(GPRequest, self).__init__()
        self.setName(self.service_name)

    def run_mytool_service(self):
        print(f"Requesting : {self.service_url}")
        req = tbx.olu_km_toolbox(5, my_gisportal, PoolRefresher.fut)  # future object is needed
        res = req.result()  # made sync

        print(f"Response of {self.service_name} : \n"
              f"{res}")

    def run(self):
        # updating: run
        PoolRefresher.run_task(self.service_name)

        # requesting
        self.run_mytool_service()

        # updating: finish
        PoolRefresher.finish_task(self.service_name)


if __name__ == '__main__':
    p = PoolRefresher()
    p.start()
