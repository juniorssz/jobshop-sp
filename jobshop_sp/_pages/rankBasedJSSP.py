import numpy as np
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid

from jobshop_sp._pages.utils import (convert_uploaded_df_to_grid,
                                     generate_input_grid, get_array,
                                     get_formulation, get_gantt, get_input_df,
                                     get_title, show_btn_download_csv,
                                     show_btn_download_results,
                                     show_solver_log, validate_input_grid)
from jobshop_sp.config.params import (JOB_COL, MACHINE_PREFIX, STAGE_PREFIX,
                                      TIME_UNITS)
from jobshop_sp.optim.disjunctiveJSSP import DisjunctiveJSSP


def get_template_tempos() -> pd.DataFrame:
    data = np.array([[5, 7, 10], [9, 5, 3], [5, 8, 2], [2, 7, 4], [8, 8, 8]])
    df = pd.DataFrame(data)
    df.columns = ["machine1", "machine2", "machine3"]
    return df


def get_template_rotas() -> pd.DataFrame:
    data = np.array([[2, 1, 3], [1, 2, 3], [3, 2, 1], [2, 1, 3], [3, 1, 2]])
    df = pd.DataFrame(data)
    df.columns = ["step1", "step2", "step3"]
    return df


def rankBasedJSSP_page(session):
    st.header(get_title(session))
    st.markdown(get_formulation(session))
    st.markdown("---")

    with st.container():
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            n_jobs = st.number_input(label="Número de tarefas", min_value=1, value=3)
        with col2:
            n_machines = st.number_input(
                label="Número de máquinas", min_value=1, value=3
            )
        with col3:
            dt_start = st.date_input("Data de início")
        with col4:
            hr_start = st.time_input("Horário de início")
        with col5:
            time_unit = st.selectbox("Unidade de tempo", tuple(TIME_UNITS.keys()))

        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            is_import_csv_selected = (
                st.radio("Dados de entrada", ["Digitar", "Importar CSV"])
                == "Importar CSV"
            )
        with col2:
            if is_import_csv_selected:
                uploaded_tp = st.file_uploader(
                    "Carregar tempos de processamento", type=["csv"]
                )
                uploaded_rp = st.file_uploader(
                    "Carregar rotas de processamento", type=["csv"]
                )

        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col2:
            if is_import_csv_selected:
                show_btn_download_csv(
                    get_template_tempos(),
                    label="Baixar template tempos",
                    filename="template_tempos.csv",
                )
        with col3:
            if is_import_csv_selected:
                show_btn_download_csv(
                    get_template_rotas(),
                    label="Baixar template rotas",
                    filename="template_rotas.csv",
                )

        if (
            is_import_csv_selected
            and uploaded_tp is not None
            and uploaded_rp is not None
        ):
            df_tp = convert_uploaded_df_to_grid(
                pd.read_csv(uploaded_tp), JOB_COL, MACHINE_PREFIX
            )
            df_rp = convert_uploaded_df_to_grid(
                pd.read_csv(uploaded_rp), JOB_COL, STAGE_PREFIX
            )
        else:
            df_tp = get_input_df(
                n_jobs, n_machines, first_col=JOB_COL, prefix=MACHINE_PREFIX
            )
            df_rp = get_input_df(
                n_jobs, n_machines, first_col=JOB_COL, prefix=STAGE_PREFIX
            )

        st.subheader("Tempos de processamento")
        df_tp = generate_input_grid(df_tp)["data"]

        st.subheader("Rotas de processamento")
        df_rp = generate_input_grid(df_rp)["data"]

        ##### Resolução do problema #####
        col1, col2, col3, col4, col5 = st.columns(5)
        with col3:
            btn_solve = st.button("Resolver")

        if btn_solve:
            df_tp, tp_is_valid, tp_log_msgs = validate_input_grid(df_tp, JOB_COL)
            if tp_is_valid:
                df_rp, rp_is_valid, rp_log_msgs = validate_input_grid(df_rp, JOB_COL)
                if not rp_is_valid:
                    for msg in rp_log_msgs:
                        st.error(msg)
            else:
                for msg in tp_log_msgs:
                    st.error(msg)

            if tp_is_valid and rp_is_valid:

                # Resolve o modelo:
                tempos = get_array(df_tp, JOB_COL)
                rotas = get_array(df_rp, JOB_COL)
                start_time = pd.to_datetime(f"{dt_start} {hr_start}")
                model = DisjunctiveJSSP(
                    tempos, rotas, start_time, TIME_UNITS[time_unit]
                )
                model.solve()

                show_solver_log(model.is_optimal, model.solver_time, model.objective)

                df_out = model.get_output_data()
                st.plotly_chart(get_gantt(df_out))

                AgGrid(df_out, height=250, enable_enterprise_modules=False)

                col1, col2, col3, col4, col5 = st.columns(5)
                with col3:
                    show_btn_download_results(df_out)
