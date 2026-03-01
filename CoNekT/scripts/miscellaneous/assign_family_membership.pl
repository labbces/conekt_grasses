#!/usr/bin/perl

use strict;
use warnings;
use Getopt::Long;

#Created by Diego Riaño 2004
#updated on 15.02.2010 by Paulino Perez
#updated on 12.03.2011 by Diego Riaño to make it understan hmmscan domtblout Hmmerv3.0 format
#updated on 2013 by Diego Riaño to make it understad hmmsearch domtblout Hmmerv3.0 format
#Updated on 29.07.2019 by DMRP, adding the type of TAP in the final output.
#Updated on 31.07.2025 by Joao Novoletti, add the alignment start and stop positions of each relevant domain.

my $version='3.3';
my $pfam_tbl='';
my $domain_list='';
my $species='';
my $family_out="";
my $license='';
my $rfile='';
my $help='';
my %famType;
my %query_al_coords;

GetOptions(
    'pfam=s'           => \$pfam_tbl,
    'species|s=s'      => \$species,
    'out|o=s'          => \$family_out,
    'rules|r=s'        => \$rfile,
    'license|l'        => \$license,
    'help|h|?'         => \$help
);

if ($help){
 &usage();
 exit(1);
}
if ($license){
 &license();
 exit(1);
}

if(!$pfam_tbl){
 &usage();
 print STDERR "You must provide the name of the PFAM domtblout file\n";
 exit(1);
}
if (!$family_out){
 &usage();
 print STDERR "You must provide the name of an output file to the family classification\n";
 exit(1)
}
if (!-s $rfile){
 &usage();
 print STDERR "Cannot find rules file [$rfile]\n\n";
 exit(1)
}

#opens familiy_out for writing
open OUTFAM, ">$family_out" or die "Cannot open $family_out for writing\n";

#open ftam_tbl (List of PFAM hits in tabular format) for reading
open PFAMTBL, "$pfam_tbl" or die "Cannot open file $pfam_tbl\n";
#It returns the entire file
my @tbl=<PFAMTBL>;
close PFAMTBL;

my @all_dom=();

open RULES, "$rfile" or die "Cannot open file $rfile\n";
my @rules=<RULES>;
my @rules1=@rules;
close RULES;

#Obtains all domains (required, forbidden) and also check 
#the number of fields in each rule
my $semicolon_counter;
foreach my $item (@rules1)
{
   my $line=$item;
   chomp $line;
   $semicolon_counter=0;
   chomp($item);
   $semicolon_counter ++ while $item=~/;/g;
   if($semicolon_counter!=3)
   {
      print "$item\n";
      die "INCORRECT number of fields \nExpecting 3 fields Got: $semicolon_counter fields \nEach field must be ended with ;\n";
   }
   $item=substr($item,index($item,";")+1,length($item)-index($item,";"));
   $item=~s/;+|=/,/g;
   $item=~s/:eq[0-9]+|:gt[0-9]+|:lt[0-9]+//g;
   push @all_dom, split(',',$item); 
   my ($familyName,$familyType)=split(/[:;]/,$line);
   $famType{$familyName}=$familyType;
}

undef my %swx;
@swx{@all_dom} = ();
@all_dom = sort keys %swx;  

#Some hashes
my %domains_per_gene;
my %gene_family;
my %evalues_per_gene;
my %evalues_gene_family;
my %domains_classification;

foreach my $tbl(@tbl)
{
    next if $tbl=~/^#/;
    next if $tbl eq '';
    chomp $tbl; #delete \n from $tbl
    #                                                                            --- full sequence --- -------------- this domain -------------   hmm coord   ali coord   env coord
# target name        accession   tlen query name           accession   qlen   E-value  score  bias   #  of  c-Evalue  i-Evalue  score  bias  from    to  from    to  from    to  acc description of target
#------------------- ---------- ----- -------------------- ---------- ----- --------- ------ ----- --- --- --------- --------- ------ ----- ----- ----- ----- ----- ----- ----- ---- ---------------------
  my ($gen_id,undef,$querylength,$domain,undef,$domainlength,undef,undef,undef,undef,undef,undef,$evalue,$score,undef,$start,$stop,$hitalgnstart,$hitalgnstop,undef,undef)=split(/\s+/,$tbl);
#  my ($domain,undef,$domainlength,$gen_id,undef,$querylength,undef,undef,undef,undef,undef,undef,$evalue,$score,undef,$hitalgnstart,$hitalgnstop,$start,$stop,undef,undef)=split(/\s+/,$tbl);

    #next if($domainlength != ($hitalgnstop-$hitalgnstart+1));
    #print $gen_id."\t$domain\n";
    next unless defined $domain;
    foreach my $dom(@all_dom){
	chomp $dom; #delete \n from dom
	if($domain eq $dom){
	    @{$gene_family{$gen_id}}=();
            @{$evalues_gene_family{$gen_id}}=();
	    $domains_per_gene{$gen_id}{$domain}+=1;
            $evalues_per_gene{$gen_id}{$domain}=$evalue;
      $query_al_coords{$gen_id}{$domain} = [$hitalgnstart, $hitalgnstop];
	}
    }
}

my @required_domains=();
my @or_required_domains=();
my @forbidden_domains=();
my @eqt_gt=();
my @eqt_gt_operator_operand=();
my $prod_required_domains;
my $prod_or_required_domains;
my $prod_forbidden_domains;
my $prod;
my $check_sum;

foreach my $gene(keys %domains_per_gene)
{
        foreach my $item (@rules) 
        {
           chomp($item);   
           my ($TFF, $required_domains, $forbidden_domains)=split(";",$item);
           my @required_domains=split(",",$required_domains); 
           my @forbidden_domains=split(",",$forbidden_domains);
           #Required domains
           my $prod_required_domains=1;
           my $sum_evalues=0;
           foreach my $item_required (@required_domains)
           { 
                @or_required_domains=split("=",$item_required);
                $prod_or_required_domains=0;
                foreach my $item_or_required (@or_required_domains)
                {
                  #check requiered domains, we have three cases a) at least one (default), but we can specify this by item_requiered:gt0
                  #                                             b) exactly some_number, specify this by item_requiered:eqtsome_number, example Myb_DNA-binding:eqt1 for MYB-related TFF
                  #                                             c) at least some_other_number + 1, specify this by item_requiered:gtsome_number, example Myb_DNA-binding:gt1 for MYB TFF  
                  #                                             d) at most  some_other_number - 1, specify this by item_requiered:ltsome_number, example AP2:lt3 for AP2-EREBP
                  if(!(($item_or_required=~/\:gt/) || ($item_or_required=~/\:eq/) || ($item_or_required=~/\:lt/)))
                  {

                    if(exists($domains_per_gene{$gene}{$item_or_required})) 
                    {
                      $prod_or_required_domains=1;
                      $sum_evalues+=$evalues_per_gene{$gene}{$item_or_required};
                    } 
                  }
                  else
                  {
                       my($case,$copynumber);
                       @eqt_gt=split(":",$item_or_required);
                       $item_or_required=$eqt_gt[0];

                       if($eqt_gt[1]=~/^(eq|gt|lt)(\d+)$/i){
                        $case=$1;
                        $copynumber=$2;
                       }
                       else{
                        die "FATAL:Number and case not allowed [@eqt_gt]!!!!!!"
                       }
                       if(lc($case) eq 'eq' )
                       {    
                            if(exists($domains_per_gene{$gene}{$item_or_required}))
                            {
                              if($domains_per_gene{$gene}{$item_or_required}==$copynumber) 
                              {
                                 $prod_or_required_domains=1;
                                 $sum_evalues+=$evalues_per_gene{$gene}{$item_or_required};
                              }
                            } 
                       }
                       if(lc($case) eq 'gt')
                       {
                           if(exists($domains_per_gene{$gene}{$item_or_required}))
                           {  
                             if($domains_per_gene{$gene}{$item_or_required}>$copynumber) 
                             {
                                $prod_or_required_domains=1;
			        $sum_evalues+=$evalues_per_gene{$gene}{$item_or_required};
                             }
                           } 
                       }
                       if(lc($case) eq 'lt')
                       {
                           if(exists($domains_per_gene{$gene}{$item_or_required}))
                           {
                             if($domains_per_gene{$gene}{$item_or_required}<$copynumber) 
                             {
                                $prod_or_required_domains=1;
 			        $sum_evalues+=$evalues_per_gene{$gene}{$item_or_required};
                             }
                           } 
                       }
                  }
                }
                if($prod_or_required_domains==0) {$prod_required_domains=0;}
           }
           #Forbidden domains
           $prod_forbidden_domains=1;
           foreach my $item_forbidden (@forbidden_domains)
           {
              if(exists($domains_per_gene{$gene}{$item_forbidden})) {$prod_forbidden_domains=0;}
           }
           $prod=($prod_required_domains)*($prod_forbidden_domains);  
           if($prod==1)
           {
              push @{$gene_family{$gene}}, $TFF;
              push @{$evalues_gene_family{$gene}},$sum_evalues;
              my @used_domains;
              foreach my $req (@required_domains) {
                  my @ors = split("=", $req);
                  foreach my $d (@ors) {
                      $d =~ s/:.*//;
                      push @used_domains, $d if exists $domains_per_gene{$gene}{$d};
                  }
              }
              $domains_classification{$gene}{$TFF} = \@used_domains;
           }
        }
}

my %saw;
undef %saw;
my @genes = grep(!$saw{$_}++, (keys %domains_per_gene));

print STDERR "There are: ".scalar(keys %domains_per_gene)." genes with TF domains\n\n";
print STDERR scalar(keys %gene_family)." genes go into analysis from ".scalar(@genes)."\n\n";

print OUTFAM "Gene\tFamily\tType\tDomain\tQuery_Start\tQuery_Stop\n";

foreach my $gene(keys %gene_family){
    if (@{$gene_family{$gene}}>1)
    {
	print STDERR "Gene $gene in more than two famlies @{$gene_family{$gene}} check that\n";
        #FIXME:Assuming that only two families are in conflict
        my $fam1=(@{$gene_family{$gene}})[0];
        my $fam2=(@{$gene_family{$gene}})[1];
        if(!(($fam1=~/TFF/ && $fam2=~/TFF/) || ($fam1=~/OTR/ && $fam2=~/OTR/))) 
        {
          print STDERR "TFF or OTR?\n";
          if($fam1=~/TFF/)
          {
             print STDERR "$gene Assigned to $fam1\n";
             if($fam1=~/_/) {print OUTFAM "$gene\t",(split("_",(split(":",$fam1))[0]))[1],"\t".$famType{(split("_",(split(":",$fam1))[0]))[1]}."\n";}
             else {print OUTFAM "$gene\t",(split(":",$fam1))[0]."\t".$famType{(split(":",$fam1))[0]}."\n";}
          }
          else
          {
            print STDERR "$gene Assigned to $fam2\n";
            if($fam2=~/_/) {print OUTFAM "$gene\t",(split("_",(split(":",$fam2))[0]))[1],"\t".$famType{(split("_",(split(":",$fam2))[0]))[1]}."\n";}
            else {print OUTFAM "$gene\t",(split(":",$fam2))[0],"\t".$famType{(split(":",$fam2))[0]}."\n";}
          }
        }
        else
        {
            print STDERR "Using Evalues\n";
            my $val1=(@{$evalues_gene_family{$gene}})[0];
            my $val2=(@{$evalues_gene_family{$gene}})[1];
            if($val1<$val2) 
            {
               print STDERR "$gene Assigned to $fam1\n";
               if($fam1=~/_/) {print OUTFAM "$gene\t",(split("_",(split(":",$fam1))[0]))[1],"\t".$famType{(split("_",(split(":",$fam1))[0]))[1]}."\n";}
               else {print OUTFAM "$gene\t",(split(":",$fam1))[0],"\t".$famType{(split(":",$fam1))[0]}."\n";}
            }
            else
            {
               print STDERR "$gene Assigned to $fam2\n";
               if($fam2=~/_/) {print OUTFAM "$gene\t",(split("_",(split(":",$fam2))[0]))[1],"\t".$famType{(split("_",(split(":",$fam2))[0]))[1]}."\n";}
               else {print OUTFAM "$gene\t",(split(":",$fam2))[0],"\t".$famType{(split(":",$fam2))[0]}."\n";}
            }
        }
    }
    elsif(@{$gene_family{$gene}} == 1)
    {
      my $gen_fam=(split(":",${$gene_family{$gene}}[0]))[0];
      if($gen_fam=~/CHECK/) {print "$gene has additional domains, not considered in the optional domains and can not be classified $gen_fam\n";}
      foreach my $fam (@{$gene_family{$gene}}) {
        my $fam_name = (split(":", $fam))[0];
        my $type = $famType{$fam_name};
        my @domains = @{$domains_classification{$gene}{$fam} || []};
        foreach my $dom (@domains) {
            my ($start, $stop) = exists $query_al_coords{$gene}{$dom} ? @{$query_al_coords{$gene}{$dom}} : ('NA', 'NA');
            print OUTFAM "$gene\t$fam_name\t$type\t$dom\t$start\t$stop\n";
        }
      }
    }
    else
    {
        print OUTFAM "$gene\tOrphans\tOrphans\n";
    }
}

sub usage{
    print STDERR "$0 version $version, Copyright (C) 2005-2015 Diego Mauricio Riaño Pachón\n";
    print STDERR "$0 version $version, Copyright (C) 2009 Paulino Perez\n";
    print STDERR "$0 comes with ABSOLUTELY NO WARRANTY; for details type `$0 -l'.\n";
    print STDERR "This is free software, and you are welcome to redistribute it under certain conditions;\n";
    print STDERR "type `$0 -l' for details.\n";
    print STDERR <<EOF;
NAME
    $0   assign proteins into TF families based on PFAM hits.

USAGE
    $0 -f file.pfam.domtbl -r rules.txt

OPTIONS
    --pfam               List of PFAM hits in tabular format (hmmsearch v3; domtblout).         REQUIRED
    --out          -o    Output file where the classification into TF families will be stored.  REQUIRED
    --rules        -r    Rules file                                                             REQUIRED
    --help,        -h    This help.
    --license,     -l    License.

EOF
}

sub license{
    print STDERR <<EOF;

Copyright (C) 2005-2015 Diego Mauricio Riaño Pachón
e-mail: diriano\@gmail.com
Coypright (c) 2009 Paulino Perez Rodriguez

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
EOF
exit;
}
