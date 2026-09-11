# Adding GO term, InterPro domain and CAZymes definition

Descriptions for GO terms, InterPro domains and CAZymes descriptions should be added before
adding functional annotation. This step should be completed first. In
the top menu click on 'Add' and select 'Functional Data'. 
 
![Add functional data](../images/add_functional_data.png "Adding functional data")

The Gene Ontology (GO) is a detailed and standardized database of information regarding the roles of genes, helping to describe genes and their products functionality across different species. The GO consists in three main ontologies concerning molecular function, cellular component and biological process.
This ontology is represented in Open Biomedical Ontologies (OBO) format, wich is a standard file format used for representing ontologies and is composed by a header, a term stanzas and finally the relationship or other annotations providing additioinal context and connections between terms.
The GO descriptions can be obtained from the Gene Ontology Consortium's 
official website in OBO format [here](http://geneontology.org/page/download-ontology).

InterPro is a resource for functional analysis of proteins, it combines 13 databases, offering comprehensive informations and annotations aswell. It helps in identifying protein functions and understanding their roles within different biological processes, including several types of information such as protein families, domains, repeats and sites.
InterPro data can be represented in XML format, which is a standard way of structuring information for easy sharing and interpretation.
InterPro domains and descriptions(called the **Entry list**) are found on EBI InterPro's download pages [here](https://www.ebi.ac.uk/interpro/download.html). 
 
‘Carbohydrate-active enZymes’ (CAZYme) refer to enzymes that participate in catalytic activities involved in sugar or sugar-derivative biotransformation. This database catalogs CAZymes by classifying them into families based on sequence similarity and functional properties. (4)
This resource provides detailed information about their sequences, structures, functions, and applications. CAZymes descriptions can be access on CAZY database [here](https://bcb.unl.edu/dbCAN2/download/Databases/).
**Decompress the .gz file prior to uploading.** 

Click the buttons on the page and select the corresponding files, next 
click 'Add functional data' to upload the files to your server and 
import them in the database. This process can take some time, do not 
close the browser window. 

**Note: The existing tables will be cleared before adding the new 
definitions. Do not update this information if GO/InterPro data is 
already added to species!**
