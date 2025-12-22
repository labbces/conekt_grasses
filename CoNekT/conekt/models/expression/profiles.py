from conekt import db
from conekt.models.condition_tissue import ConditionTissue
from conekt.models.relationships.sample_literature import SampleLitAssociation
from conekt.models.literature import LiteratureItem

import json
import contextlib
from statistics import mean
from math import log
from sqlalchemy.dialects.mysql import LONGTEXT

from sqlalchemy.orm import joinedload, undefer
from flask import flash

SQL_COLLATION = None


class ExpressionProfile(db.Model):
    __tablename__ = 'expression_profiles'
    id = db.Column(db.Integer, primary_key=True)
    species_id = db.Column(db.Integer, db.ForeignKey('species.id', ondelete='CASCADE'), index=True)
    probe = db.Column(db.String(80, collation=SQL_COLLATION), index=True)
    sequence_id = db.Column(db.Integer, db.ForeignKey('sequences.id', ondelete='CASCADE'), index=True)
    profile = db.deferred(db.Column(LONGTEXT))

    specificities = db.relationship('ExpressionSpecificity',
                                    backref=db.backref('profile', lazy='joined'),
                                    lazy='dynamic',
                                    cascade="all, delete-orphan",
                                    passive_deletes=True)

    def __init__(self, probe, sequence_id, profile):
        self.probe = probe
        self.sequence_id = sequence_id
        self.profile = profile

    @staticmethod
    def get_values(data, lit_dict=None):
        """
        Gets an object for values in data

        :param data: Dict with expression profile
        :param lit_dict: Dict with literature information (optional)
        :return: Object of conditions and values
        """
        processed_values = {}
        for key, expression_values in data["data"]["tpm"].items():
            condition_value = data["data"]["annotation"][key]
            literature_doi = data["data"]["lit_doi"][key]

            if condition_value not in processed_values:
                if lit_dict is None:
                    processed_values[condition_value] = []
                else:
                    author_name = lit_dict[literature_doi].capitalize()
                    processed_values[condition_value + " (" + author_name + ")"] = []

            if lit_dict is None:
                processed_values[condition_value].append(expression_values)
            else:
                author_name = lit_dict[literature_doi].capitalize()
                processed_values[condition_value + " (" + author_name + ")"].append(expression_values)
        
        return processed_values


    @staticmethod
    def __profile_to_table(data):
        """
        Internal function to convert an expression profile (dict) to a tabular text

        :param data: Dict with expression profile
        :return: table (string)
        """
        output = [["condition", "mean", "min", "max"]]
        order = data["order"]
        processed_values = ExpressionProfile.get_values(data)

        for o in order:
            try:
                values = processed_values[o]
                output.append([o,
                               str(mean(values)),
                               str(min(values)),
                               str(max(values))
                               ])
            except Exception as e:
                print(e)

        return '\n'.join(['\t'.join(l) for l in output])

    @property
    def table(self):
        """
        Returns the condition expression as a tabular text file

        :return: table with data (string)
        """
        table = ExpressionProfile.__profile_to_table(json.loads(self.profile))

        return table

    def tissue_table(self, condition_tissue_id, use_means=True):
        """
        Returns the tissue expression as a tabular text file

        :param condition_tissue_id: condition_tissue_id for the conversion
        :param use_means: Use the mean of the condition (recommended)
        :return: table with data (string)
        """
        table = ExpressionProfile.__profile_to_table(self.tissue_profile(condition_tissue_id,
                                                                         use_means=use_means)
                                                     )
        return table

    @property
    def low_abundance(self, cutoff=10):
        """
        Checks if the mean expression value in any conditions in the plot is higher than the desired cutoff

        :param cutoff: cutoff for expression, default = 10
        :return: True in case of low abundance otherwise False
        """
        data = json.loads(self.profile)
        processed_values = ExpressionProfile.get_values(data)

        checks = [mean(v) > cutoff for _, v in processed_values.items()]

        return not any(checks)

    @staticmethod
    def convert_profile(condition_to_tissue, profile_data, use_means=True):
        """
        Convert a full, detailed profile into a more general summarized one using conversion table stored in the
        database

        :param condition_to_tissue: dict with conversion instructions
        :param profile_data: profile to convert
        :param use_means: use means of detailed condition if True otherwise use samples independently. Default True
        :return: New profile
        """
        tissues = list(set(condition_to_tissue['conversion'].values()))

        output = {}

        for t in tissues:
            valid_conditions = [k for k in profile_data['data'] if k in condition_to_tissue['conversion'] and condition_to_tissue['conversion'][k] == t]
            valid_values = []
            for k, v in profile_data['data'].items():
                if k in valid_conditions:
                    if use_means:
                        valid_values.append(mean(v))
                    else:
                        valid_values += v

            output[t] = valid_values if len(valid_values) > 0 else [0]

        return {'order': condition_to_tissue['order'],
                'colors': condition_to_tissue['colors'],
                'data': output}

    def tissue_profile(self, condition_tissue_id, use_means=True):
        """
        Applies a conversion to the profile, grouping several condition into one more general feature (e.g. tissue).

        :param condition_tissue_id: identifier of the conversion table
        :param use_means: store the mean of the condition rather than individual values. The matches the spm
        calculations better.
        :return: parsed profile
        """
        ct = ConditionTissue.query.get(condition_tissue_id)

        condition_to_tissue = json.loads(ct.data)
        profile_data = json.loads(self.profile)

        output = ExpressionProfile.convert_profile(condition_to_tissue, profile_data, use_means=use_means)

        return output

    @staticmethod
    def get_heatmap(species_id, probes, zlog=True, raw=False):
        """
        Returns a heatmap for a given species (species_id) and a list of probes. It returns a dict with 'order'
        the order of the experiments and 'heatmap' another dict with the actual data. Data is zlog transformed

        :param species_id: species id (internal database id)
        :param probes: a list of probes to include in the heatmap
        :param zlog: enable zlog transformation (otherwise normalization against highest expressed condition)
        """
        profiles = ExpressionProfile.query.options(undefer('profile')).filter_by(species_id=species_id).\
            filter(ExpressionProfile.probe.in_(probes)).all()
        
        lit_info = SampleLitAssociation.query.with_entities(SampleLitAssociation.literature_id).filter_by(species_id=species_id).distinct().all()

        literatures = LiteratureItem.query.filter(LiteratureItem.id.in_([lit_id[0] for lit_id in lit_info]))

        lit_dict = {}

        for lit in literatures:
            author_name = lit.author_names
            author_name = author_name.capitalize()
            if lit.qtd_author > 1:
                lit_dict[lit.doi] = f'{author_name} et al., {lit.public_year}'
            else:
                lit_dict[lit.doi] = f'{author_name}, {lit.public_year}'

        order = []
        output = []
        not_found = [p.lower() for p in probes]

        for profile in profiles:
            name = profile.probe
            data = json.loads(profile.profile)

            with contextlib.suppress(ValueError):
                not_found.remove(profile.probe.lower())

            with contextlib.suppress(ValueError):
                not_found.remove(profile.sequence.name.lower())
            
            processed_values = ExpressionProfile.get_values(data, lit_dict)

            values = {}

            order = list(processed_values.keys())

            for o in order:
                values[o] = mean(processed_values[o])

            row_mean = mean(values.values())
            row_max = max(values.values())

            for o in order:
                if zlog:
                    if row_mean == 0 or values[o] == 0:
                        values[o] = '-'
                    else:
                        try:
                            values[o] = log(values[o]/row_mean, 2)
                        except ValueError as _:
                            print("Unable to calculate log()", values[o], row_mean)
                            values[o] = '-'
                else:
                    if row_max != 0 and not raw:
                        values[o] = values[o]/row_max

            output.append({"name": name,
                           "values": values,
                           "sequence_id": profile.sequence_id,
                           "shortest_alias": profile.sequence.shortest_alias})

        if len(not_found) > 0:
            flash("Couldn't find profile for: %s" % ", ".join(not_found), "warning")

        return {'order': order, 'heatmap_data': output}

    @staticmethod
    def get_po_heatmap(species_id, probes, pos, zlog=True, raw=False):
        """
        Returns a heatmap for a given species (species_id), a list of probes and a list of ontologies. It returns a dict with 'order'
        the order of the experiments and 'heatmap' another dict with the actual data. Data is zlog transformed

        :param species_id: species id (internal database id)
        :param probes: a list of probes to include in the heatmap
        :param pos: a list of po classes to include in the heatmap
        :param zlog: enable zlog transformation (otherwise normalization against highest expressed condition)
        """

        profiles = ExpressionProfile.query.options(undefer('profile')).filter_by(species_id=species_id).\
            filter(ExpressionProfile.probe.in_(probes)).all()

        order = []
        output = []
        not_found = [p.lower() for p in probes]

        for profile in profiles:
            name = profile.probe
            data = json.loads(profile.profile)

            if pos:
                order = pos
            else:
                order = data['order']

            with contextlib.suppress(ValueError):
                not_found.remove(profile.probe.lower())

            with contextlib.suppress(ValueError):
                not_found.remove(profile.sequence.name.lower())
            
            values = {}

            for o in order:
                for key, value in data['data']['po_anatomy_class'].items():
                    if value == o:
                        if value in values.keys():
                            values[o].append(data['data']['tpm'][key])
                        else:
                            values[o] = [data['data']['tpm'][key]]
                
                print(values[o], "\n\n\n\n\n\n")
                values[o] = mean(values[o])

            row_max = max(list(values.values()))

            for v in values:
                if zlog:
                    if values[v] == 0:
                        values[v] = '-'
                    else:
                        try:
                            values[v] = log(values[v], 2)
                        except ValueError as _:
                            print("Unable to calculate log()", values[v])
                            values[v] = '-'
                else:
                    if row_max != 0 and not raw:
                        values[v] = values[v]/row_max

            output.append({"name": name,
                           "values": values,
                           "sequence_id": profile.sequence_id,
                           "shortest_alias": profile.sequence.shortest_alias})

        if len(not_found) > 0:
            flash("Couldn't find profile for: %s" % ", ".join(not_found), "warning")

        return {'labels':order, 'order': order, 'heatmap_data': output}
    
    @staticmethod
    def get_peco_heatmap(species_id, probes, pecos, zlog=True, raw=False):
        """
        Returns a heatmap for a given species (species_id), a list of probes and a list of ontologies. It returns a dict with 'order'
        the order of the experiments and 'heatmap' another dict with the actual data. Data is zlog transformed

        :param species_id: species id (internal database id)
        :param probes: a list of probes to include in the heatmap
        :param pecos: a list of peco classes to include in the heatmap
        :param zlog: enable zlog transformation (otherwise normalization against highest expressed condition)
        """

        profiles = ExpressionProfile.query.options(undefer('profile')).filter_by(species_id=species_id).\
            filter(ExpressionProfile.probe.in_(probes)).all()

        order = []
        output = []
        not_found = [p.lower() for p in probes]

        for profile in profiles:
            name = profile.probe
            data = json.loads(profile.profile)

            if pecos:
                order = pecos
            else:
                order = set(data['data']['peco_class'].values())

            with contextlib.suppress(ValueError):
                not_found.remove(profile.probe.lower())

            with contextlib.suppress(ValueError):
                not_found.remove(profile.sequence.name.lower())
            
            values = {}

            for o in order:
                for key, value in data['data']['peco_class'].items():
                    if value == o:
                        if value in values.keys():
                            values[o].append(data['data']['tpm'][key])
                        else:
                            values[o] = [data['data']['tpm'][key]]
                
                values[o] = mean(values[o])

            row_max = max(list(values.values()))

            for v in values:
                if zlog:
                    if values[v] == 0:
                        values[v] = '-'
                    else:
                        try:
                            values[v] = log(values[v], 2)
                        except ValueError as _:
                            print("Unable to calculate log()", values[v])
                            values[v] = '-'
                else:
                    if row_max != 0 and not raw:
                        values[v] = values[v]/row_max

            output.append({"name": name,
                           "values": values,
                           "sequence_id": profile.sequence_id,
                           "shortest_alias": profile.sequence.shortest_alias})

        if len(not_found) > 0:
            flash("Couldn't find profile for: %s" % ", ".join(not_found), "warning")

        return {'labels':order, 'order': order, 'heatmap_data': output}

    @staticmethod
    def get_profiles(species_id, probes, limit=1000):
        """
        Gets the data for a set of probes (including the full profiles), a limit can be provided to avoid overly
        long queries

        :param species_id: internal id of the species
        :param probes: probe names to fetch
        :param limit: maximum number of probes to get
        :return: List of ExpressionProfile objects including the full profiles
        """
        profiles = ExpressionProfile.query.\
            options(undefer('profile')).\
            filter(ExpressionProfile.probe.in_(probes)).\
            filter_by(species_id=species_id).\
            options(joinedload('sequence').load_only('name').noload('xrefs')).\
            limit(limit).all()

        return profiles
