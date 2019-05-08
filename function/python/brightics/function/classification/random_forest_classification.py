"""
    Copyright 2019 Samsung SDS
    
    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at
    
        http://www.apache.org/licenses/LICENSE-2.0
    
    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sklearn.utils
from sklearn.ensemble import RandomForestClassifier 
from brightics.common.repr import BrtcReprBuilder
from brightics.common.repr import strip_margin
from brightics.common.repr import plt2MD
from brightics.common.repr import dict2MD
from brightics.common.groupby import _function_by_group
from brightics.common.utils import check_required_parameters
from brightics.common.utils import get_default_from_parameters_if_required
from brightics.common.validation import validate
from brightics.common.validation import greater_than_or_equal_to
from brightics.common.validation import raise_error


def random_forest_classification_train(table, group_by=None, **params):
    check_required_parameters(_random_forest_classification_train, params, ['table'])
    
    params = get_default_from_parameters_if_required(params, _random_forest_classification_train)
    param_validation_check = [greater_than_or_equal_to(params, 1, 'n_estimators'),
                              greater_than_or_equal_to(params, 1, 'max_depth'),
                              greater_than_or_equal_to(params, 1, 'min_samples_split'),
                              greater_than_or_equal_to(params, 1, 'min_samples_leaf')]
    validate(*param_validation_check)
    
    if group_by is not None:
        return _function_by_group(_random_forest_classification_train, table, group_by=group_by, **params)
    else:
        return _random_forest_classification_train(table, **params)


def _plot_feature_importances(feature_cols, classifier):
    
    feature_importance = classifier.feature_importances_
    indices = np.argsort(feature_importance)
    sorted_feature_cols = np.array(feature_cols)[indices]
    
    n_features = classifier.n_features_
    plt.barh(range(n_features), feature_importance[indices], color='b', align='center')
    for i, v in enumerate(feature_importance[indices]):
        plt.text(v, i, " {:.2f}".format(v), color='b', va='center', fontweight='bold')
    
    plt.yticks(np.arange(n_features), sorted_feature_cols)
    plt.xlabel("Feature importance")
    plt.ylabel("Feature")
    plt.tight_layout()
    fig_feature_importances = plt2MD(plt)
    plt.close()
    return fig_feature_importances
    
    
def _random_forest_classification_train(table, feature_cols, label_col,
                                 n_estimators=10, criterion="gini", max_depth=None, min_samples_split=2, min_samples_leaf=1,
                                 min_weight_fraction_leaf=0, max_features="sqrt",
                                 max_leaf_nodes=None, min_impurity_decrease=0, class_weight=None, random_state=None):   
    
    X_train = table[feature_cols]
    y_train = table[label_col]   

    if(sklearn.utils.multiclass.type_of_target(y_train) == 'continuous'):
        raise_error('0718', 'label_col')
    
    if max_features == "None":
        max_features = None
          
    if class_weight is not None:
        if y_train.dtype == str:
            classes = sorted(list(set(y_train)), key=str.lower)
        else:
            classes = sorted(list(set(y_train)))

        weights = class_weight
        class_weight = {classes[0]: weights[0]}
        for i in range(1, len(classes)):
            class_weight[classes[i]] = weights[i]  
    
    classifier = RandomForestClassifier(n_estimators=n_estimators,
                                        criterion=criterion,
                                        max_depth=max_depth,
                                        min_samples_split=min_samples_split,
                                        min_samples_leaf=min_samples_leaf,
                                        min_weight_fraction_leaf=min_weight_fraction_leaf,
                                        max_features=max_features,
                                        max_leaf_nodes=max_leaf_nodes,
                                        min_impurity_decrease=min_impurity_decrease,
                                        class_weight=class_weight,
                                        random_state=random_state)
    classifier.fit(X_train, y_train) 

    params = {'feature_cols': feature_cols,
             'label_col': label_col,
             'n_estimators': n_estimators,
             'criterion': criterion,
             'max_depth': max_depth,
             'min_samples_split': min_samples_split,
             'min_samples_leaf': min_samples_leaf,
             'min_weight_fraction_leaf': min_weight_fraction_leaf,
             'max_features': max_features,
             'max_leaf_nodes': max_leaf_nodes,
             'min_impurity_decrease': min_impurity_decrease,
             'class_weight': class_weight,
             'random_state': random_state}
    
    model = dict()
    model['classifier'] = classifier
    model['params'] = params

    fig_feature_importances = _plot_feature_importances(feature_cols, classifier)
           
    rb = BrtcReprBuilder()
    rb.addMD(strip_margin("""
    | ## Random Forest Classification Train Result
    |
    | ### Parameters
    | {params}
    |
    | ### Feature Importance
    | {fig_feature_importances}
    |
    """.format(params=dict2MD(params), fig_feature_importances=fig_feature_importances)))
        
    model['_repr_brtc_'] = rb.get()   
               
    return {'model' : model}


def random_forest_classification_predict(table, model, **params):
    check_required_parameters(_random_forest_classification_predict, params, ['table', 'model'])
    if '_grouped_data' in model:
        return _function_by_group(_random_forest_classification_predict, table, model, **params)
    else:
        return _random_forest_classification_predict(table, model, **params)


def _random_forest_classification_predict(table, model, pred_col_name='prediction', prob_col_prefix='probability', suffix='index'):
    out_table = table.copy()
    classifier = model['classifier']
    test_data = table[model['params']['feature_cols']]
    
    out_table[pred_col_name] = classifier.predict(test_data)   
    
    classes = classifier.classes_
    if suffix == 'index':
        suffixes = [i for i, _ in enumerate(classes)]
    else:
        suffixes = classes
        
    prob = classifier.predict_proba(test_data)
    prob_col_name = ['{prob_col_prefix}_{suffix}'.format(prob_col_prefix=prob_col_prefix, suffix=suffix) for suffix in suffixes]    
    out_col_prob = pd.DataFrame(data=prob, columns=prob_col_name)

    out_table = pd.concat([out_table, out_col_prob], axis=1)
    return {'out_table': out_table}
