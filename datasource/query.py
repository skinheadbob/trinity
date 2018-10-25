from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Union

import pandas as pd
from pyspark.sql import DataFrame

from .spec import Mode

DEF_HOW = 'inner'
DEF_LSUFFIX = '_l'
DEF_RSUFFIX = '_r'


class Query(ABC):
    def __init__(self,
                 mode: Mode):
        self._mode = mode

    def load_df(self) -> Union[DataFrame, pd.DataFrame]:
        if self.mode is Mode.BATCH:
            return self._load_spark_df()
        elif self.mode is Mode.REALTIME:
            return self._load_pandas_df()

    def join(self, the_other_query, on=None, repartition=None,
             how=DEF_HOW, lsuffix=DEF_LSUFFIX, rsuffix=DEF_RSUFFIX):
        if on is None:
            raise ValueError('must specify "on"')
        return PipelinedQuery(self).join(the_other_query, on, repartition,
                                         how=how, lsuffix=lsuffix, rsuffix=rsuffix)

    def union(self, the_other_query, repartition=None):
        return PipelinedQuery(self).union(the_other_query, repartition=repartition)

    @abstractmethod
    def _load_spark_df(self) -> DataFrame:
        pass

    @abstractmethod
    def _load_pandas_df(self) -> pd.DataFrame:
        pass

    @property
    def mode(self) -> Mode:
        return self._mode


class PipelinedQuery:
    def __init__(self, query: Query):
        self.query_list = [query]
        self.op_list = []

    def join(self, query: Query, on,
             repartition=None,
             how=DEF_HOW, lsuffix=DEF_LSUFFIX, rsuffix=DEF_RSUFFIX):
        if query.mode != self.mode:
            raise RuntimeError('cannot mix queries of different modes')
        self.query_list.append(query)
        self.op_list.append(Operator(Operation.JOIN,
                                     on=on, repartition=repartition,
                                     how=how, lsuffix=lsuffix, rsuffix=rsuffix))
        return self

    def union(self, query: Query, repartition=None):
        if query.mode != self.mode:
            raise RuntimeError('cannot mix queries of different modes')
        self.query_list.append(query)
        self.op_list.append(Operator(Operation.UNION, repartition=repartition))

    def load_df(self) -> Union[DataFrame, pd.DataFrame]:
        with ThreadPoolExecutor() as pool:
            future_list = [pool.submit(query.load_df) for query in self.query_list]
            df_list = [future.result() for future in future_list]
        if len(df_list) == 1:
            return df_list[0]

        left_df = df_list[0]
        for df_idx in range(1, len(df_list)):
            right_df = df_list[df_idx]
            op_idx = df_idx - 1
            op = self.op_list[op_idx]
            left_df = op.exec(left_df, right_df)

        return left_df

    @property
    def mode(self):
        return self.query_list[0].mode


class Operation(Enum):
    JOIN = 'join'
    UNION = 'union'


class Operator:
    def __init__(self, op: Operation, **kwargs):
        self._op = op
        self.kwargs = kwargs

    def exec(self,
             left_df: Union[DataFrame, pd.DataFrame],
             right_df: Union[DataFrame, pd.DataFrame]) -> Union[DataFrame, pd.DataFrame]:
        if self._op == Operation.JOIN:
            return self._join(left_df, right_df)
        elif self._op == Operation.UNION:
            return self._union(left_df, right_df)

        raise NotImplementedError()

    def _join(self,
              left_df: Union[DataFrame, pd.DataFrame],
              right_df: Union[DataFrame, pd.DataFrame]) -> Union[DataFrame, pd.DataFrame]:
        on = self.kwargs.get('on')
        repartition = self.kwargs.get('repartition', None)
        how = self.kwargs.get('how')

        if type(left_df) is DataFrame:
            if repartition is None:
                return left_df.join(right_df, on=on, how=how)
            return left_df.repartition(repartition) \
                .join(right_df.repartition(repartition), on=on, how=how)
        elif type(left_df) is pd.DataFrame:
            lsuffix = self.kwargs.get('lsuffix')
            rsuffix = self.kwargs.get('rsuffix')
            return pd.merge(left_df, right_df, how=how,
                            left_on=on, right_on=on, suffixes=(lsuffix, rsuffix))
        raise NotImplementedError()

    def _union(self,
               left_df: Union[DataFrame, pd.DataFrame],
               right_df: Union[DataFrame, pd.DataFrame]) -> Union[DataFrame, pd.DataFrame]:
        repartition = self.kwargs.get('repartition', None)

        if type(left_df) is DataFrame:
            if repartition is None:
                return left_df.union(right_df)
            return left_df.union(right_df).repartition(repartition)
        elif type(left_df) is pd.DataFrame:
            return pd.concat(left_df, right_df)

        raise NotImplementedError()
