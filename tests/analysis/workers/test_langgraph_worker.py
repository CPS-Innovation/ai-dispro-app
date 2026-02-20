import pytest

from src.analysis.workers import LangGraphWorker
from src.database import init_session_manager, get_session


@pytest.mark.integration
@pytest.mark.parametrize(("experiment_id","text", "save_results"), [
    (
         "TST-EXP-test_langgraph_worker",
         """On 25/10/16 a number of 999 calls were made to the Police from concerned members of the public reporting an incident on [XXX] ROAD, [XXX] in the vicinity "[XXX] CHIPPY".\n\nDuring the call the caller states that a Silver/ grey VAUXHALL CORSA was damaged.\n\nWitness and one of the original callers witness [WITNESS1] will state:\n\nHe was conducting work in the area at approximately 1030hrs when he was stood at the junction of [XXX] ROAD and [XXX] ROAD, he has seen a male in company with other males brandishing a machete which he says is around 3 feet in length.\n\nA car has then gone past of which he could not describe the make, model or even colour as he was focussed on the machete the male has then hit the vehicle with the machete.\n\nHe describes hearing a bang and then could see what looked like a wing mirror and parts down at the male\'s feet. The male 3 has then tried to conceal the machete up his top and down his trousers but it was too big so he ran down the back of [XXX], emerging a few moments later without a machete and with a mobile in his left hand and a small knife in his right hand.\n\nHe describes this male as Afro-Caribbean male, around 25-30yrs old, around 5\'10" tall and of slim build. Short black hair, around a 3 in length. Cannot say if he had facial hair. Wearing a long sleeved puffa style jacket which was blue, zipped up at the front and looked slightly oversized for him. Dark blue jogging bottoms and possibly dark coloured trainers. He describes the Machete as around 2-3 feet in length with a faded wooden handle and a dulled silvery coloured blade.\n\nPC [PC3] Attended the incident at 1110hours and observed two males stood outside the Laundrette on [XXX] ROAD of similar description to those involved in the incident.\n\nUpon seeing the Police vehicle one of the males ran down the ginnel at the side of the [XXX] sandwich shop headed towards [XXX] CLOSE.\n\nThe other male was detained by the officers and was identified as [SUSPECT] he stated\n\n"I HAVEN\'T DONE ANYTHING, IF I HAD I\'D HAVE RUN."\n\n[SUSPECT] was arrested for Affray and possession of a bladed article in a public place.\n\nInformation received to Police identified [SUSPECT] as feuding with a male called [XXX].\n\nSince this incident a silver/ grey VAUXHALL ASTRA [XXX] located by PC [PC4] on the wasteland off [XXX] AVENUE, [XXX] which is situated less than 100 meters away from [XXX] home address.\n\nThe vehicle was locked and secure and had a damaged driver\'s side wing mirror with a missing wing mirror case and a shattered mirror consistent with the damage caused on the date of the incident.     """,
         True,
    )
])
def test_worker(experiment_id, text, save_results):

    init_session_manager()

    worker = LangGraphWorker(
        config={
            "theme_id": "theme1",
            "pattern_id": "not_fact",
        },
        save_results=save_results,
    )

    if save_results:

         with get_session() as session:
            from src.repositories import (
                ExperimentRepository,
                AnalysisJobRepository,
                SectionRepository,
                VersionRepository,
                DocumentRepository,
                CaseRepository,
            )
            CaseRepository(session).upsert(id=1, urn="01TS0000008")
            DocumentRepository(session).upsert(id=1, case_id=1)
            VersionRepository(session).upsert(id=1, document_id=1)
            ExperimentRepository(session).upsert(id=experiment_id)
            SectionRepository(session).upsert(id=29, version_id=1, experiment_id=experiment_id, redacted_content="Content")
            AnalysisJobRepository(session).upsert(id=0, section_id=29, experiment_id=experiment_id)
            
    results = worker.analyze(
        text=text,
        experiment_id=experiment_id,
        section_id=29,
        analysis_job_id=0,
    )

    assert isinstance(results, list)
    assert len(results) >= 1