"""Guard the pinned native UPDATE worker against duplicate Celery delivery."""
from pathlib import Path
import sysconfig

def apply(path):
    source=path.read_text(encoding='utf-8')
    marker='# COSS: lock and reuse an already ingested UPDATE'
    if marker in source:return source
    old='classified = await session.get(IncomingClassifiedData, ingest_id)'
    assert source.count(old)==1,'Pinned UPDATE worker changed; review retry guard'
    source=source.replace(old,'classified = (await session.execute(select(IncomingClassifiedData).where(\n                    IncomingClassifiedData.ingest_id == ingest_id).with_for_update())).scalar_one_or_none()')
    anchor='                if (\n                    classified.pipeline_action'
    assert source.count(anchor)==1,'Pinned UPDATE dispatch changed; review retry guard'
    source=source.replace(anchor,'                '+marker+'\n                if classified.ingestion_status == ProcessStatusEnum.PROCESSED.value and classified.change_request_id:\n                    return\n'+anchor)
    compile(source,str(path),'exec')
    path.write_text(source,encoding='utf-8')
    return source

if __name__=='__main__':
    apply(Path(sysconfig.get_path('purelib'))/'openg2p_registry_celery_worker/tasks/change_request_ingest_worker.py')
