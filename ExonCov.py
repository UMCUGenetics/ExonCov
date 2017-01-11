#! /usr/bin/env python
import sys
import os
import shutil
import glob
import re
import commands
#import getopt
#import datetime
import time
from optparse import OptionParser
from optparse import Option, OptionGroup
import os.path
#from operator import itemgetter

###########################################################################################################################################
# AUTHOR: M.G. Elferink
# DATE: 18-06-2015
# Purpose: This script is used to calculate the coverage of exons, transcripts, preferred transcripts, gene-panels based on BAM input files
###########################################################################################################################################

#######


def unique(list):
    seen = set()
    seen_add = seen.add
    return [x for x in list if not (x in seen or seen_add(x))]

#######


def make_Dic(list):
    dic = {}
    for item in list:
        try:
            dic[item.rstrip()]
        except:
            dic[item.rstrip()] = []
    return dic

########


def Write_SH(job_num, wkdir, sambamba, bam_file, bq, mq, L_list, threads, bed_file):
    sambamba_filter = "mapping_quality >= {mq} and not duplicate and not failed_quality_control and not secondary_alignment".format(mq=mq)
    prefix, _ = os.path.basename(bam_file).rsplit(".", 1)
    out_file = "{}_exon_coverage.tsv".format(prefix)
    command = '{sambamba} depth region {bam_file} -m -q {bq} -F " {sambamba_filter} "'.format(
        sambamba=sambamba,
        bam_file=bam_file,
        bq=bq,
        sambamba_filter=sambamba_filter,
    )
    command += ' {thresholds} -t {threads} -L {bed_file} -o {out_file}\n'.format(
        thresholds=" ".join("-T {}".format(threshold) for threshold in L_list),
        threads=threads,
        bed_file=bed_file,
        out_file=out_file,
    )
    script_file = os.path.join(wkdir, "Depth_job_{}.sh".format(job_num))
    with open(script_file, "w") as f:
        f.write(command)
    return script_file, out_file

########


def one_more_minute(timeslot):
    hours, minutes, seconds = (int(s) for s in timeslot.split(":"))
    extra_hours, minutes = divmod(minutes + 1, 60)
    return ":".join(("{:02d}".format(n) for n in (hours + extra_hours, minutes, seconds)))

########


def wait_for_job_ids(job_ids, queue, project, timeslot, wkdir):
    hold_script = os.path.join(wkdir, "Hold_job_exoncov_depth.sh")
    with open(hold_script, "w") as f:
        f.write("echo Finished" + "\n")
    qsub = "qsub -cwd -q {queue} {project} -l h_rt={timeslot} -l h_vmem=1G -hold_jid {hold_job_ids} {hold_script}".format(
        queue=queue,
        project="-P {}".format(project) if project else "",
        timeslot=one_more_minute(timeslot),
        hold_job_ids=",".join(job_ids),
        hold_script=hold_script,
    )
    hold_job_id = commands.getoutput(qsub).split()[2]
    test = commands.getoutput("qstat -j " + hold_job_id)
    while True:
        if "do not exist" in test:
            break
        else:
            time.sleep(5)
            test = commands.getoutput("qstat -j " + hold_job_id)


########


def submit_jobs(job_list, queue, project, timeslot, max_mem, threads, wkdir):
    job_ids = []
    for job in job_list:
        qsub = "qsub -q {queue} {project} -l h_rt={timeslot} -l h_vmem={max_mem}G -R y -cwd -pe threaded {threads} {job}".format(
            queue=queue,
            project="-P {}".format(project) if project else "",
            timeslot=timeslot,
            max_mem=max_mem,
            threads=threads,
            job=job,
        )
        job_id = commands.getoutput(qsub).split()[2]
        job_ids.append(job_id)
    wait_for_job_ids(job_ids, queue, project, timeslot, wkdir)

########


def make_Exon_stats(sambamba, wkdir, threads, flanks, mq, bq, timeslot, input_files, queue, project, max_mem):
    exoncov_files = []
    job_list = []
    for job_num, bam_file in enumerate(input_files, start=1):
        job, out_file = Write_SH(job_num, wkdir, sambamba, bam_file, bq, mq, L_list, threads, bed_file)
        job_list.append(job)
        exoncov_files.append(out_file)

    if len(job_list) == 0:
        sys.exit("No BAM files detected")
    else:
        submit_jobs(job_list, queue, project, timeslot, max_mem, threads, wkdir)
    return exoncov_files

########


def make_Dic_Trans(exoncov, column):
    dic_trans = {}
    for line in exoncov:
        splitline = line.split()
        if "#" not in splitline[0]:  # skip header
            for item in splitline[column].split(":"):  # split on multiple transcripts (must be ":" seperated!)
                try:
                    dic_trans[item]
                    dic_trans[item] += [splitline]
                except:
                    dic_trans[item] = [splitline]
    return dic_trans

#######


def make_Transcript_stats(exoncov_files, L_bed, L_list, column, NM_ENS_dic):
    error_file = open("error_file.out", "w")
    dic_panel = {}
    error_dic = {}
    transcript_files = []
    for file in exoncov_files:
        exoncov = open(str(file), "r").readlines()
        dic_trans = make_Dic_Trans(exoncov, column)  # make dictionary for transcripts with all exons
        transcript_list = []
        for item in dic_trans:
            final_list = []
            for exon in dic_trans[item]:
                list = []
                # Gene, chromosome, from, to, interval (too hardcoded, change?)
                list += item, exon[4], exon[0], exon[1], exon[2], int(exon[2]) - int(exon[1])
                # add number of bases covered in total for target
                list += [int("%.0f" % float(float(int(exon[2]) - int(exon[1])) * (float(exon[8]))))]
                # int(L_bed+3)-1)= length BED file + 3 output fields sambamaba (-1 for offset). len(L_list) = values as input -L option sambamba
                for cov in exon[(int(L_bed + 3) - 1):((int(L_bed + 3) - 1) + int(len(L_list)))]:
                    bases = ((int(exon[2]) - int(exon[1])) * float(cov))
                    list.append(float(bases))
                list.append(exon[total_length - 1])  # last value = sample name
                final_list.append(list)
            if len(final_list) == 1:
                printline = final_list[0]
                printline += [int("1")]  # add number of exons to last column
            else:
                chr = str(final_list[0][2])
                start = int(final_list[0][3])
                stop = int(final_list[0][4])
                x = 0
                for region in final_list[1:]:  # [1:] because first exon already covered

                    if start < stop and int(region[3]) < int(region[4]) and start < int(region[3]) and stop < int(region[4]) and chr == str(region[2]):
                        if x == 0:
                            printline = final_list[0]
                            printline += [int("1")]  # add number of exons to last column
                            x = 1
                        printline[4] = int(region[4])  # replace old stop by new stop
                        y = 0
                        while y < len(L_list) + 2:  # +2 for length and total_bases
                            printline[5 + y] += float(region[5 + y])
                            y += 1
                        printline[-1] += 1
                        chr = str(region[2])
                        start = int(region[3])
                        stop = int(region[4])
                    else:
                        printline = ""
                        try:
                            error_dic[item]
                        except:
                            error_dic[item] = str(region[2]), region[-1]

            if len(printline) > 0:  # convert bases covered >X to percentage based on total transcript length
                transcript_line = [printline[0]]
                try:
                    transcript_line += [NM_ENS_dic[str(printline[0])]]  # use gene name if transcript is found in NM file!
                except:
                    transcript_line += [printline[1]]  # otherwise, use gene name of BED file. This can include multiple names seperated by ":"

                transcript_line += printline[2:5]
                transcript_line += [str(printline[-1])]
                transcript_line += [str("%.0f" % float(printline[5]))]  # add number of total_bases of total bases for combined exons
                y = 0
                while y < len(L_list) + 1:  # +1 for mean coverage column
                    transcript_line += [str(float(float(printline[6 + y]) / float(printline[5])))]
                    y += 1
                transcript_line += [printline[-2]]
                transcript_list += [transcript_line]
                printline = ""

        transcript_list.sort(key=lambda x: (x[2], int(x[3])))
        write_file = open(str(transcript_list[0][-1]) + "_transcript_coverage.tsv", "w")  # Output file for transcript coverage
        transcript_files += [str(transcript_list[0][-1]) + "_transcript_coverage.tsv"]
        write_file.write("#Transcript\tGene\tChr\tStart\tStop\t#exons\tTotal_bases\tMean_Coverage\t")
        for item in L_list:
            write_file.write(">" + str(item) + "\t")
        write_file.write("Sample\n")
        for item in transcript_list:
            for sub in item:
                write_file.write(str(sub) + "\t")
            write_file.write("\n")
        write_file.close()
        print "\tFinished Transcript coverage for sample: " + str(transcript_list[0][-1])
        for item, error in error_dic.items():
            error_file.write("Transcript has multiple hits in the genome: " + str(item) + " from sample " + str(error[1]) + "\n")
    error_file.close()
    return transcript_files, dic_trans, error_dic

########


def check_Longer(dic, splititem, pref, pref_gene_dic, gene_dic):
    if "NM_" in splititem[0]:
        if int(splititem[6]) > int(dic[splititem[1]][1]):  # replace item if longer transcript
            dic[splititem[1]] = [splititem[0], splititem[6], splititem[5], pref]
        elif int(splititem[6]) == int(dic[splititem[1]][1]):  # replace item if transcript is equal, but less exons (will this ever happen??)
            if int(splititem[5]) > int(dic[splititem[1]][2]):
                dic[splititem[1]] = [splititem[0], splititem[6], splititem[5], pref]
    else:  # if not NM transcript
        x = 0
        for item in gene_dic[splititem[1]]:
            if "NM_" in item:
                x += 1
        if x == 0:
            if int(splititem[6]) > int(dic[splititem[1]][1]):  # replace item if longer transcript
                dic[splititem[1]] = [splititem[0], splititem[6], splititem[5], pref]
            elif int(splititem[6]) == int(dic[splititem[1]][1]):  # replace item if transcript is equal, but less exons (will this ever happen??)
                if int(splititem[5]) > int(dic[splititem[1]][2]):
                    dic[splititem[1]] = [splititem[0], splititem[6], splititem[5], pref]
                else:
                    pass
            else:
                pass
    return(dic)

#########


def get_Longest_Transcript(transcript_files, pref_gene_dic, pref_dic, gene_dic):
    # longest transcript needs to be determined for only 1 sample as BED files used are the same!
    transcript = open(str(transcript_files[0]), "r").readlines()
    dic = {}
    for item in transcript:
        if "#" not in item:
            splititem = item.split()
            try:
                pref_dic[splititem[0]]
                try:
                    pref_gene_dic[pref_dic[splititem[0]][0]]
                    if len(pref_gene_dic[pref_dic[splititem[0]][0]]) > 1:
                        pref = "no"  # >>> go for longest transcript
                    else:
                        pref = "yes"
                        dic[splititem[1]] = [splititem[0], splititem[6], splititem[5], str(pref)]  # Transcipt is preferred, push into dictionary.
                except:
                    pref = "no"  # >>> go for longest transcript
            except:
                pref = "no"  # >>> go for longest transcript

            if pref == "no":  # only when preferred transcript is not known/ unclear due to multiple transcripts.
                try:
                    dic[splititem[1]]
                    if dic[splititem[1]][3] == "yes":
                        pass  # There is already a preferred transcript in the dictionary, so skip
                    else:
                        dic = check_Longer(dic, splititem, pref, pref_gene_dic, gene_dic)
                except:
                    if "NM_" in splititem[0]:  # only include NM transcripts! This is the first entry for NM.
                        dic[splititem[1]] = [splititem[0], splititem[6], splititem[5], str(pref)]
                    else:
                        x = 0
                        try:
                            for item in gene_dic[splititem[1]]:
                                if "NM_" in item:
                                    x += 1
                            if x == 0:
                                dic[splititem[1]] = [splititem[0], splititem[6], splititem[5], str("no")]
                        except:
                            print "Error, gene not found", splititem[1]
    return dic

###########


def pref_Dic(preferred):
    pref_dic = {}
    for line in preferred:
        if "#" not in line:
            splitline = line.split()
            try:
                pref_dic[splitline[1].split(".")[0]]
                # prevent double entries because of missing version in transcript ID
                if pref_dic[splitline[1].split(".")[0]][1] == splitline[1].split(".")[0]:
                    pass
                else:
                    pref_dic[splitline[1].split(".")[0]] += [splitline[0]]
            except:
                pref_dic[splitline[1].split(".")[0]] = [splitline[0]]
    return pref_dic

#############


def pref_Gene_Dic(pref_dic):
    pref_gene_dic = {}
    for item in pref_dic:
        try:
            pref_gene_dic[pref_dic[item][0]] += [item]
        except:
            pref_gene_dic[pref_dic[item][0]] = [item]
    return pref_gene_dic


#############

def gene_Dic(dic_trans):
    gene_dic = {}
    for item in dic_trans:
        for line in dic_trans[item]:
            for gene in line[1].split(":"):
                try:
                    gene_dic[gene]
                    gene_dic[gene] = unique(gene_dic[gene] + [item])
                except:
                    gene_dic[gene] = [item]
    return gene_dic

###########


def make_NM_ENS_dic(hgnc):
    try:  # make dictionary of all known ENST/NM to HGNC
        NM_ENS_dic = {}
        NM_gene = open(str(hgnc), "r").readlines()
        for line in NM_gene:
            splitline = line.split()
            if "#" not in line:
                try:
                    NM_ENS_dic[splitline[1]]
                    print "Warning: transcript has been found more than once:" + str(splitline[1])
                except:
                    NM_ENS_dic[splitline[1]] = splitline[0]
    except:
        sys.exit("NM file not found")

    return NM_ENS_dic

#########


def calc_Panel_Cov(transcript_files):
    for file in transcript_files:
        print "\nWorking on gene panels for sample " + str(file.split("_")[0])
        trans = open(file, "r").readlines()
        list = []
        for line in trans:
            splitline = line.split()
            if "#" not in splitline[0]:
                try:
                    dic[splitline[1]]
                    if dic[splitline[1]][0] == splitline[0]:
                        list += [splitline]
                except:
                    error_collection.write("Gene does not exist in transcript file! " + str(splitline[1]) + "\n")

        dic_preferred = {}
        write_file1 = open(str(file[:-24]) + "_preferred_transcripts_coverage.tsv", "w")
        write_file1.write("#Preferred_transcript\tGene\tChr\tStart\tStop\tExons\tTotal_bases\tMean_Coverage\t")
        for cover in L_list:
            write_file1.write(">" + str(cover) + "\t")
        write_file1.write("Sample" + "\n")
        for item in list:
            try:
                dic_preferred[item[1]]
            except:
                dic_preferred[item[1]] = item
            for line in item:
                write_file1.write(str(line) + "\t")
            write_file1.write("\n")
        write_file1.close()

        print "Working on coverage of gene panels "
        write_file2 = open(str(file.split("_")[0]) + "_gene_panel_coverage_all.tsv", "w")
        printline = "Gene_panel\tDescription\tTotal_size(bp)\tAverage_Coverage\t"
        for value in L_list:
            printline += ">" + str(value) + "\t"
        printline += "Genes_in_panel\tSample\tMissing_genes_in_panel"

        all_genes = []
        for item in dic_preferred:
            all_genes += [item]

        write_file2.write(printline + "\n")
        for line in panel_list:
            if "#" in line:
                pass
            else:
                splitline = line.split()
                list = []
                total_list = [0] * (len(L_list) + 6)
                total_list[0:2] = splitline[0:2]
                incomplete = []
                if splitline[2] == "ALL":
                    genes = all_genes  # Use list of all genes here to calculate coverage of the exome!
                    pass
                else:
                    genes = splitline[2].split(",")
                    genes = unique(genes)  # make gene list unique

                for item in genes:
                    try:
                        dic_preferred[item]
                        x = 3
                        for value in dic_preferred[item][7:7 + 1 + int(len(L_list))]:  # +1 because of avr coverage
                            trans_bases = float(dic_preferred[item][6])
                            prev_trans_bases = float(total_list[2])
                            total_bases = float(dic_preferred[item][6]) * float(value)
                            prev_total_bases = float(total_list[2]) * float(total_list[x])
                            new_cov = float((total_bases + prev_total_bases) / (trans_bases + prev_trans_bases))
                            total_list[x] = new_cov
                            x += 1
                        total_list[2] += int(dic_preferred[item][6])
                        total_list[x] = splitline[2]
                    except:
                        error_collection.write("Gene " + str(item) + " does not exist in Gene-panel " + str(splitline[0]) + "\n")
                        incomplete += [str(item)]
                total_list[x + 1] = file.split("_")[0]

                if len(incomplete) == 0:
                    for item in total_list:
                        write_file2.write(str(item) + "\t")
                    write_file2.write("complete\n")

                    try:
                        panel_coverage[total_list[0]]
                        panel_coverage[total_list[0]] += [total_list + ["complete"]]
                    except:
                        panel_coverage[total_list[0]] = [total_list + ["complete"]]
                else:
                    for item in total_list:
                        write_file2.write(str(item) + "\t")
                    write_file2.write("incomplete")
                    for item in incomplete:
                        write_file2.write("_" + str(item))
                    try:
                        panel_coverage[total_list[0]]
                        panel_coverage[total_list[0]] += [total_list + ["incomplete"]]
                    except:
                        panel_coverage[total_list[0]] = [total_list + ["incomplete"]]
                    write_file2.write("\n")
        write_file2.close()
    return panel_coverage

########


def make_html(transcript_files, pwd):  # Print all Gen-panel per sample results in a HTML page
    def Color(value):
        color_map = ("#FF0000", "#FF2000", "#FF4000", "#FF6000", "#FF8000", "#FF9900", "#FFAA00", "#FFCC00",
                     "#FFDD00", "#FFFF00", "#DDFF00", "#CCFF00", "#AAFF00", "#99FF00", "#60FF00", "#20FF00", "#00CC00")
        limit_map = ("20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80", "85", "90", "95", "100")
        x = 0
        color = color_map[0]
        for item in limit_map:
            if float(item) <= float(value):
                color = color_map[x]
            x += 1
        return color
    html_files = []
    for file in transcript_files:
        HTML_file = open(os.path.join(wkdir, file.split("_")[0] + ".html"), "w")
        html_files.append(file.split("_")[0] + ".html")
        sample = file.split("_")[0]
        file = open(file.split("_")[0] + "_gene_panel_coverage_all.tsv", "r").readlines()
        HTML_file.write(
            "<!DOCTYPE html>\n<html>\n<head>\n<style>\ntable, th, td {\n    border: 1px solid grey;\n    border-collapse: collapse;\n}\nth, td {\n    padding: 1px;\n    text-align: center;\n}\ntable th        {\n    background-color: lightgrey;\n    color: black;\n}\n\n</style>\n</head>\n<body>\n\n<table style=\"width:100%\">\n")
        HTML_file.write("<caption><font size=6>Sample=" + str(sample) + " Run=" + str(pwd) + "</font></caption>\n")
        for line in file:
            incomplete = []
            if "Missing_genes_in_panel" in line:  # = header
                HTML_file.write("<tr>\n")
                splitline = line.split()[0:-3]
                for item in splitline[0:4]:
                    HTML_file.write(" <th>\t" + str(item) + "\t</th>\n")
                for item in splitline[4:]:
                    HTML_file.write(" <th>\t" + str(item) + "\t</th>\n")
                HTML_file.write("</tr>\n")

            elif "incomplete" in line:  # = skip incomplete gen-panels
                incomplete += line.split()[0:2]
                pass
            else:  # fill HTML cells
                HTML_file.write("<tr>\n")
                splitline = line.split()[0:-2]
                for item in splitline[0:3]:  # Column 1-3: Gene_panel/Decription/Total_size
                    HTML_file.write(" <td>\t" + str(item) + "\t</td>\n")

                if float(splitline[3]) < 50:  # Column 4: Coverage
                    HTML_file.write(" <td BGCOLOR=\" #FF0000  \" >\t" + str("%.2f" % float(splitline[3])) + "\t</td>\n")
                elif float(splitline[3]) >= 50 and float(splitline[3]) < 100:
                    HTML_file.write(" <td BGCOLOR=\" #FF9900  \" >\t" + str("%.2f" % float(splitline[3])) + "\t</td>\n")
                elif float(splitline[3]) >= 100 and float(splitline[3]) < 200:
                    HTML_file.write(" <td BGCOLOR=\" #AAFF00  \" >\t" + str("%.2f" % float(splitline[3])) + "\t</td>\n")
                elif float(splitline[3]) >= 200:
                    HTML_file.write(" <td BGCOLOR=\" #00CC00 \" >\t" + str("%.2f" % float(splitline[3])) + "\t</td>\n")

                for item in splitline[4:4 + int(len(L_list))]:  # Column 5- end:  coverage percentage
                    color = Color(item)
                    HTML_file.write(" <td BGCOLOR=\"" + str(color) + "\">\t" + str("%.2f" % float(item)) + "\t</td>\n")
                HTML_file.write("</tr>\n")
        HTML_file.write("</table>\n</body>\n")
        HTML_file.close()
    return html_files

###########


def glob_move(source_glob, dest_dir):
    for f in glob.glob(source_glob):
        shutil.move(f, dest_dir)

###########


def cleanup_results(results_dir, exoncov_files, html_files):
    if os.path.isdir(results_dir):
        shutil.rmtree(results_dir)

    for sub_dir in ["Exons", "All_transcripts", "Preferred_transcripts", "Gene_panel_coverage_sample", "SH"]:
        d = os.path.join(results_dir, sub_dir)
        if not os.path.isdir(d):
            os.makedirs(d)

    glob_move(r"*preferred_transcripts_coverage.tsv", os.path.join(results_dir, "Preferred_transcripts"))
    glob_move(r"*transcript_coverage.tsv", os.path.join(results_dir, "All_transcripts"))
    glob_move(r"*gene_panel_coverage_all.tsv", os.path.join(results_dir, "Gene_panel_coverage_sample"))
    glob_move(r"*coverage_*.tsv", results_dir)
    glob_move(r"*error*", results_dir)
    glob_move(r"Depth_job*sh*", os.path.join(results_dir, "SH"))
    glob_move(r"Hold_job_exoncov_depth*sh*", os.path.join(results_dir, "SH"))

    for f in html_files:
        shutil.move(f, results_dir)

    for f in exoncov_files:
        shutil.move(f, os.path.join(results_dir, "Exons"))

###########


def find_input_files(wkdir, search_pattern):
    input_files = []
    bam_files = commands.getoutput("find {} -iname '*bam'".format(wkdir)).split()
    for bam_file in bam_files:
        match = re.search(search_pattern, bam_file)  # For Illumina data only via IAP
        if match:
            input_files.append(bam_file)
    return input_files


#########################################

class MultipleOption(Option):
    ACTIONS = Option.ACTIONS + ("extend",)
    STORE_ACTIONS = Option.STORE_ACTIONS + ("extend",)
    TYPED_ACTIONS = Option.TYPED_ACTIONS + ("extend",)
    ALWAYS_TYPED_ACTIONS = Option.ALWAYS_TYPED_ACTIONS + ("extend",)

    def take_action(self, action, dest, opt, value, values, parser):
        if action == "extend":
            values.ensure_value(dest, []).append(value)
        else:
            Option.take_action(self, action, dest, opt, value, values, parser)

#########################################


if __name__ == "__main__":
    parser = OptionParser()
    group = OptionGroup(parser, "Main options")

    ######
    #group.add_option("-i", default="dedup.bam$",metavar="[FILE]",dest="input_files", help="Input BAM file(s)[default = search for dedup.bam$]")

    PROG = os.path.basename(os.path.splitext(__file__)[0])
    long_commands = ('categories')
    short_commands = {'cat': 'categories'}
    parser = OptionParser(option_class=MultipleOption, usage='usage: %prog ', version='%s' % (PROG))
    parser.add_option("-o", default="Exoncov_v3", dest="exoncov_folder", metavar="[PATH]", help="full name of output folder [default = Exoncov_v3]")
    parser.add_option('-d', default="dedup.bam$", type="string", dest='search_pattern',
                      metavar='[FILE]', help="Search pattern for BAM file(s)(dedup.bam$[default]|dedup.realigned.bam$)")
    parser.add_option('-i', action="extend", type="string", dest='input_files', metavar='[FILE]', help="Input BAM file(s)[default = off]")
    parser.add_option("-a", default="02:00:00", dest="timeslot", metavar="[INT]", help="timeslot used for qsub [default = 02:00:00]")
    parser.add_option("--queue", default="all.q", dest="queue", metavar="[STRING]", help="SGE queue [default = all.q]")
    parser.add_option("--project", metavar="[STRING]", help="SGE project [default = SGE default]")
    parser.add_option("-c", default="off", dest="max_mem", metavar="[INT]", help="memory reserved for qsub [default =  off (=threads*10G)]")

    parser.add_option("-b", default="/hpc/cog_bioinf/diagnostiek/production/Dx_resources/Tracks/ENSEMBL_UCSC_merged_collapsed_sorted_v2_20bpflank.bed",
                      dest="bed_file", metavar="[PATH]", help="full path to BED file [default = [master]/ENSEMBL_UCSC_merged_collapsed_sorted_v2_20bpflank.bed]")
    parser.add_option("-n", default="/hpc/cog_bioinf/diagnostiek/production/Dx_resources/Exoncov/NM_ENSEMBL_HGNC.txt", dest="hgnc_trans_file",
                      metavar="[PATH]", help="full path to file with the link between GENE (HGNC) and all known NM/ENST transcripts [default = [master]/NM_ENSEMBL_HGNC.txt]")

    parser.add_option("-p", default="/hpc/cog_bioinf/diagnostiek/production/Dx_resources/Exoncov/Preferred_transcript_list.txt", dest="pref_file",
                      metavar="[PATH]", help="full path to Preferred transcript file [default = [master]/Preferred_transcript_list.txt]")
    parser.add_option("-l", default="/hpc/cog_bioinf/diagnostiek/production/Dx_resources/Exoncov/gpanels.txt", dest="panel_list",
                      metavar="[PATH]", help="full path to Gene panel file [default = [master]/gpanels.txt]")
    parser.add_option("-s", default="/hpc/local/CentOS7/cog_bioinf/sambamba_v0.6.1/sambamba_v0.6.1", dest="sambamba",
                      metavar="[PATH]", help="full path to sambamba [default = /hpc/local/CentOS7/cog_bioinf/sambamba_v0.6.1/sambamba_v0.6.1]")
    parser.add_option("-w", default="./", dest="wkdir", metavar="[PATH]", help="full path for  working directory [default = ./]")
    parser.add_option("-t", default=4, dest="threads", metavar="[INT]", help="number of threads [default = 4]")
    parser.add_option("-f", default=20, dest="flanks", metavar="[INT]", help="### currently disabled!### size of flanks in bp [default = 20]")
    parser.add_option("-k", default=7, dest="transcript_column", metavar="[INT]",
                      help="column in BED file that contains the transcripts [default = 7]")
    parser.add_option("-q", default=10, dest="bq", metavar="[INT]", help="minimum base quality used [default = 10]")
    parser.add_option("-m", default=20, dest="mq", metavar="[INT]", help="minimum mapping quality used [default = 20]")

    if len(sys.argv) == 1:
        parser.parse_args(['--help'])
    (opt, args) = parser.parse_args()
    threads = int(opt.threads)
    if str(opt.max_mem) == "off":
        max_mem = int(threads) * 10
    else:
        max_mem = int(opt.max_mem)

    bed_file = opt.bed_file
    hgnc = opt.hgnc_trans_file
    preferred = open(str(opt.pref_file), "r").readlines()
    panel_list = open(str(opt.panel_list), "r").readlines()
    L_list = [1, 5, 10, 15, 20, 30, 40, 50, 75, 100, 200]  # List of -L parameters for Sambamba
    L_bed = int(len(open(str(bed_file), "r").readline().split()))  # number of columns in BED file. Needed later on for correct positions in lists.
    total_length = len(L_list) + L_bed + 3  # total length of list (3 = total reads column sambamba + avr coverage sambamba + sample name)
    hgnc = opt.hgnc_trans_file
    sambamba = str(opt.sambamba)
    wkdir = str(opt.wkdir)
    flanks = int(opt.flanks)  # not incorperated yet!
    column = int(opt.transcript_column) - 1
    NM_ENS_dic = make_NM_ENS_dic(hgnc)  # make dictionary of all known ENST/NM to HGNC
    error_collection = open("error_collection_run", "w")
    bq = str(opt.bq)
    mq = str(opt.mq)
    timeslot = str(opt.timeslot)
    queue = str(opt.queue)
    exoncov_folder = str(opt.exoncov_folder)

    if not opt.input_files:
        input_files = find_input_files(wkdir, opt.search_pattern)
    else:
        input_files = opt.input_files

    print "Working on Exon coverage ({})".format(input_files)
    exoncov_files = make_Exon_stats(sambamba, wkdir, threads, flanks, mq, bq, timeslot, input_files, queue, opt.project,
                                    max_mem)  # Make Exon coverage file for each dedup.realigned.bam file

    print "Working on Transcript coverage ({})".format(exoncov_files)
    # Combine the coverage of each exon for all transcripts in the BAM file.
    trans_stats = make_Transcript_stats(exoncov_files, L_bed, L_list, column, NM_ENS_dic)
    transcript_files = trans_stats[0]
    exoncov = open(str(transcript_files[0]), "r").readlines()
    dic_trans = make_Dic_Trans(exoncov, 0)  # remake dic_tranc for _transcript_coverage.tsv file to remove redundant transcripts
    gene_dic = gene_Dic(dic_trans)  # make dictionary for all transcript for each genes.
    pref_dic = pref_Dic(preferred)  # make dictionary for preferred transcripts
    pref_gene_dic = pref_Gene_Dic(pref_dic)  # make dictionary for all genes of preferred transcripts

    print "Working on preferred Transcript ({})".format(transcript_files)
    # get preferred transcript, or if not known, the longest NM or ENST transcript.
    dic = get_Longest_Transcript(transcript_files, pref_gene_dic, pref_dic, gene_dic)
    panel_coverage = {}

    pwd = commands.getoutput("pwd").split("/")[-1]  # Assumes last folder in PWD is the run name.
    print "Working on gene panel coverage"
    panel_coverage = calc_Panel_Cov(transcript_files)
    html_files = make_html(transcript_files, pwd)
    x = 0
    print "Working on gene-panels"
    F_list = ["Coverage"] + L_list
    for cov in F_list:
        write_file3 = open(str(pwd) + "_coverage_" + str(cov) + ".tsv", "w")
        write_list = []
        for item in panel_list:   # print same order as in other Gene_panel file
            if "#" not in item:
                list = []
                list = panel_coverage[item.split()[0]][0][0:2]
                sample_list = ["Gene_panel", "Description"]
                for line in panel_coverage[item.split()[0]]:
                    if str(line[-1]) == "complete":
                        list += ["%.2f" % float(line[x + 3])]
                    else:
                        list += ["NA"]
                    sample_list += [line[-2]]
                write_list += [list]
        x += 1
        for item in sample_list:
            write_file3.write(str(item) + "\t")
        write_file3.write("\n")
        for item in write_list:
            for col in item:
                write_file3.write(str(col) + "\t")
            write_file3.write("\n")
        write_file3.close()
    error_collection.close()
    cleanup_results(os.path.join(wkdir, exoncov_folder), exoncov_files, html_files)
    print("\n################\nScript completed\n################")
