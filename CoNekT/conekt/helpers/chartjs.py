import json
from statistics import mean, stdev

from utils.color import __COLORS_RGBA as COLORS


def prepare_profiles_download(profiles, normalize=False):
    """
    Function to convert a list of NetworkProfiles to a dict compatible with chart.js

    :param profiles: list of profiles to include in the plot
    :param normalize: normalize the profiles (the max value of each profile is scaled to 1)

    :return dict with plot compatible with Chart.js
    """

    if len(profiles) > 0:
        data = json.loads(profiles[0].profile)

    # initiate output array with header
    output = ['sample\tgene\ttpm\tpo\tpeco']

    for key in data['data']['tpm'].keys():
        for count, p in enumerate(profiles):
            profile = json.loads(p.profile)
            label = key
            gene = p.probe if p.sequence_id is None else p.sequence.name
            tpm = profile['data']['tpm'][key]
            po = profile['data']['po_anatomy'][key]

            if key in profile['data']['peco']:
                peco = profile['data']['peco'][key]
            else:
                peco = 'null'

            if normalize:
                max_tpm = max(data['data']['tpm'].values())
                tpm_normalized = tpm / max_tpm if max_tpm > 0 else 0
                tpm = tpm_normalized

            output.append(label + '\t' + gene + '\t' + str(tpm) + '\t' + po + '\t' + peco)

    return '\n'.join(output)


def prepare_profiles(profiles, normalize=False, xlabel='', ylabel='', peco=False):
    """
    Function to convert a list of NetworkProfiles to a dict compatible with chart.js

    :param profiles: list of profiles to include in the plot
    :param normalize: normalize the profiles (the max value of each profile is scaled to 1)
    :param xlabel: label for x-axis
    :param ylabel: label for y-axis

    :return dict with plot compatible with Chart.js
    """

    samples = []
    datasets = []
    sample_annotations = []

    if len(profiles) > 0:
        data = json.loads(profiles[0].profile)

        if peco:
            samples = list(key for key in data['data']['tpm'].keys() if key in data['data']['peco_class'].keys())
            ontology_classes = list(data['data']['peco_class'].values())
        else:
            samples = list(data['data']['tpm'].keys())
            ontology_classes = list(data['data']['po_anatomy_class'].values())

        sample_annotations = list(data['data']['annotation'].values())

        labels_samples = [f'{sample} ({sample_annotation}/{ontology_class})' for sample, ontology_class, sample_annotation in zip(samples, ontology_classes, sample_annotations)]

    for count, p in enumerate(profiles):
        data = json.loads(p.profile)
        if peco:
            expression_values = list(data['data']['tpm'][key] for key in data['data']['tpm'].keys() if key in data['data']['peco_class'].keys())
        else:
            expression_values = list(data['data']['tpm'].values())

        if normalize:
            if expression_values == []:
                expression_values = [0]
                
            max_expression = max(expression_values)
            expression_values = [value/max_expression if max_expression > 0 else None for value in expression_values]

        datasets.append({
            'label': p.probe if p.sequence_id is None else p.sequence.name,
            'fill': True,
            'showLine': True,
            'backgroundColor': "rgba(220,220,220,0.1)" if len(profiles) > 12 else COLORS[count],
            'borderColor': "rgba(175,175,175,0.2)" if len(profiles) > 12 else COLORS[count],
            'pointRadius': 3 if len(profiles) < 13 else 0,
            'data': expression_values
        })

    output = {
        'type': 'line',
        'data': {
            'labels': labels_samples,
            'datasets': datasets
        },
        "options": {
          "legend": {
            "display": len(profiles) < 13
          },
          "tooltips": {
            "enabled": len(profiles) < 13,
            "mode": 'label',
            "intersect": False
          },
          "scales": {
              "xAxes": [{
                "scaleLabel": {
                      "display": xlabel != '',
                      "labelString": xlabel
                  },
                "gridLines": {
                    "display": True
                },
                "ticks": {
                    "maxRotation": 90,
                    "minRotation": 90
                }
              }
              ],
              "yAxes": [{
                "scaleLabel": {
                    "display": ylabel != '',
                    "labelString": ylabel
                },
                "ticks": {
                    "beginAtZero": True
                }
              }
              ]
          },
          "pan" : {
              "enabled": True,
              "mode": 'y'
          },
          "zoom": {
              "enabled": True,
              "mode": 'y'
          }
        }
    }

    return output


def prepare_avg_profiles(profiles, xlabel='', ylabel=''):
    """
    Takes a set of profiles and generates the average profile

    :param profiles: list of profiles to include in the plot
    :param xlabel: label for x-axis
    :param ylabel: label for y-axis

    :return dict with plot compatible with Chart.js
    """
    labels = []
    datasets = []

    background_color=[]
    point_color=[]

    means = []
    stdevs = []

    if len(profiles) > 0:
        data = json.loads(profiles[0].profile)
        labels = data['order']

        background_color = data["colors"] if "colors" in data.keys() else "rgba(175,175,175,0.2)"
        point_color = "rgba(55,55,55,0.4)" if "colors" in data.keys() else "rgba(220,22,22,1)"

    for p in profiles:
        data = json.loads(p.profile)

        processed_values = {}
        for key, values in data["data"]["tpm"].items():
            po_value = data["data"]["po_anatomy_class"][key]

            if po_value not in processed_values:
                processed_values[po_value] = []

            processed_values[po_value].append(values)

        expression_values = [mean(processed_values[label]) for label in labels]

        max_expression = max(expression_values)
        expression_values = [value/max_expression if max_expression != 0 else 0 for value in expression_values]

        datasets.append(expression_values)

    for i, l in enumerate(labels):
        values = [d[i] for d in datasets]
        means.append(mean(values))
        if len(values) > 1:
            # Can't get stdev for 1 value
            stdevs.append(stdev(values))
        else:
            stdevs.append(None)

    output = {"type": "bar",
              "data": {
                      "labels": list(label.capitalize() for label in data["order"]),
                      "counts": [None]*len(data["order"]),
                      "datasets": [
                          {
                            "type": "line",
                            "label": "Mean - Stdev",
                            "fill": False,
                            "showLine": False,
                            "pointBorderColor": point_color,
                            "pointBackgroundColor": point_color,
                            "data": [m - sd for m, sd in zip(means, stdevs)]
                          }, {
                            "type": "line",
                            "label": "Mean + Stdev",
                            "fill": False,
                            "showLine": False,
                            "pointBorderColor": point_color,
                            "pointBackgroundColor": point_color,
                            "data": [m + sd for m, sd in zip(means, stdevs)]
                          }, {
                            "label": "Mean",
                            "backgroundColor": background_color,
                            "data": means
                          }]
                      },
              "options": {
                  "legend": {
                    "display": False
                  },
                  "scales": {
                      "xAxes": [{
                        "scaleLabel": {
                              "display": xlabel != '',
                              "labelString": xlabel
                          },
                        "gridLines": {
                            "display": False
                        },
                        "ticks": {
                            "maxRotation": 90,
                            "minRotation": 90
                        }
                      }
                      ],
                      "yAxes": [{
                          "scaleLabel": {
                              "display": ylabel != '',
                              "labelString": ylabel
                          },
                          "ticks": {
                            "beginAtZero": True
                        }
                      }
                      ]
                  },
                  "pan" : {
                      "enabled": True,
                      "mode": 'y'
                  },
                  "zoom": {
                      "enabled": True,
                      "mode": 'y'
                  }
              }
              }

    return output


def prepare_expression_profile(data, show_sample_count=False, xlabel='', ylabel=''):
    """
    Converts data from Expression Profile to a format compatible with Chart.js

    :param data: dat from Expression Profile model
    :param show_sample_count: includes the number of samples in the plot
    :param xlabel: label for x-axis
    :param ylabel: label for y-axis
    :return: dict compatible with Chart.js
    """
    processed_means = {}
    processed_mins = {}
    processed_maxs = {}
    counts = {}
    processed_values = {}
    po_list = []

    for key, expression_values in data["data"]["tpm"].items():
        po_value = data["data"]["po_anatomy_class"][key]

        if po_value not in processed_values:
            processed_values[po_value] = []

        processed_values[po_value].append(expression_values)

    for po_value, values in processed_values.items():
        processed_means[po_value] = mean(values)
        processed_mins[po_value] = min(values)
        processed_maxs[po_value] = max(values)
        counts[po_value] = len(values)

    background_color = data["colors"] if "colors" in data.keys() else "rgba(175,175,175,0.2)"
    point_color = "rgba(55,55,55,0.4)" if "colors" in data.keys() else "rgba(220,22,22,1)"

    output = {"type": "bar",
              "data": {
                      "labels": list([c.capitalize() for c in data["order"]]),
                      "counts": list([counts[c] for c in data["order"]]) if show_sample_count else [None]*len(data["order"]),
                      "datasets": [
                          {
                            "type": "line",
                            "label": "Minimum",
                            "fill": False,
                            "showLine": False,
                            "pointBorderColor": point_color,
                            "pointBackgroundColor": point_color,
                            "data": list([processed_mins[c] for c in data["order"]])
                          },
                          {
                            "type": "line",
                            "label": "Maximum",
                            "fill": False,
                            "showLine": False,
                            "pointBorderColor": point_color,
                            "pointBackgroundColor": point_color,
                            "data": list([processed_maxs[c] for c in data["order"]])
                          },
                          {
                            "label": "Mean",
                            "backgroundColor": background_color,
                            "data": list([processed_means[c] for c in data["order"]])
                          }
                        ]
                      },
              "options": {
                  "legend": {
                    "display": False
                  },
                  "scales": {
                      "xAxes": [{
                        "scaleLabel": {
                              "display": xlabel != '',
                              "labelString": xlabel
                          },
                        "gridLines": {
                            "display": False
                        },
                        "ticks": {
                            "maxRotation": 90,
                            "minRotation": 90
                        }
                      }
                      ],
                      "yAxes": [{
                          "scaleLabel": {
                              "display": ylabel != '',
                              "labelString": ylabel
                          },
                          "ticks": {
                            "beginAtZero": True
                        }
                      }
                      ]
                  },
                  "pan" : {
                      "enabled": True,
                      "mode": 'y'
                  },
                  "zoom": {
                      "enabled": True,
                      "mode": 'y'
                  }
              }
              }

    return output


def prepare_profile_comparison(data_first, data_second, labels, normalize=1, xlabel='', ylabel=''):
    processed_first_means = {}
    processed_second_means = {}

    for key, expression_values in data_first["data"].items():
        processed_first_means[key] = mean(expression_values)
    for key, expression_values in data_second["data"].items():
        processed_second_means[key] = mean(expression_values)

    first_max = max([v for _, v in processed_first_means.items()])
    second_max = max([v for _, v in processed_second_means.items()])

    if normalize == 1:
        for k, v in processed_first_means.items():
            processed_first_means[k] = v/first_max

        for k, v in processed_second_means.items():
            processed_second_means[k] = v/second_max

    output = {"type": "bar",
              "data": {
                          "labels": list(data_first["order"]),
                          "datasets": [{
                              "label": labels[0],
                              "backgroundColor": "rgba(220,22,22,0.5)",
                              "data": list([processed_first_means[c] for c in data_first["order"]])},
                              {
                              "label": labels[1],
                              "backgroundColor": "rgba(22,22,220,0.5)",
                              "data": list([processed_second_means[c] for c in data_second["order"]])}]
              },
              "options": {
                  "legend": {
                    "display": True
                  },
                  "scales": {
                      "xAxes": [{
                        "scaleLabel": {
                              "display": xlabel != '',
                              "labelString": xlabel
                        },
                        "gridLines": {
                            "display": False
                        },
                        "ticks": {
                            "maxRotation": 90,
                            "minRotation": 90
                        }
                      }
                      ],
                      "yAxes": [{
                        "scaleLabel": {
                            "display": ylabel != '',
                            "labelString": ylabel
                        },
                        "ticks": {
                            "beginAtZero": True
                        }
                      }
                      ]
                  },
                  "pan" : {
                      "enabled": True,
                      "mode": 'y'
                  },
                  "zoom": {
                      "enabled": True,
                      "mode": 'y'
                  }
              }
              }

    return output


def prepare_doughnut(counts):
    output = {
        "data": {
            "labels": [counts[s]["label"] for s in counts.keys()],
            "datasets": [{
                "data": [counts[s]["value"] for s in counts.keys()],
                "backgroundColor": [counts[s]["color"] for s in counts.keys()],
                "hoverBackgroundColor": [counts[s]["color"] for s in counts.keys()]
            }]
        }
        ,
        "type": "doughnut"
    }

    return output
