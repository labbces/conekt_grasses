from conekt import db

class FamilyTRAssociation(db.Model):
    __tablename__ = 'family_tr'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    gene_family_id = db.Column(db.Integer, db.ForeignKey('gene_families.id', ondelete='CASCADE')) #resultado do orthofinder id da familia definida pelo orthofinder

    tr_family_id = db.Column(db.Integer, db.ForeignKey('transcription_regulator.id', ondelete='CASCADE'))

    gene_family = db.relationship('GeneFamily', backref=db.backref('tr_annotations',
                                                                   lazy='dynamic',
                                                                   passive_deletes=True), lazy='joined') #mudar

    domain = db.relationship('Interpro', backref=db.backref('family_associations',
                             lazy='dynamic', passive_deletes=True), lazy='joined') #Mudar
    
    #tabela separada para associação de dominios e trs