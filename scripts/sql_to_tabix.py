import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ExonCov import app, db
from ExonCov.models import Sample

temp_dir = '/hpc/cog_bioinf/diagnostiek/projects/Validation_ExonCov_v3.0.0/tabix_files'
bgzip_path = '/hpc/local/CentOS7/cog_bioinf/tabix-0.2.6/bin/bgzip'
tabix_path = '/hpc/local/CentOS7/cog_bioinf/tabix-0.2.6/bin/tabix'
EXON_MEASUREMENTS_RSYNC_PATH = 'douglasspar:/data/exoncov/'

with app.app_context() as current_app:

    for sample in Sample.query.all():
        print sample
        sample.exon_measurement_file = '{0}_{1}_{2}.txt'.format(sample.id, sample.project.name, sample.name)
        db.session.add(sample)
        db.session.commit()
        
        exon_measurement_file_path = '{0}/{1}'.format(temp_dir, sample.exon_measurement_file)
        exon_measurement_file = open(exon_measurement_file_path, "w")

        exon_measurement_file.write(
            '#{chr}\t{start}\t{end}\t{cov}\t{perc_10}\t{perc_15}\t{perc_20}\t{perc_30}\t{perc_50}\t{perc_100}\n'.format(
                chr='chr',
                start='start',
                end='end',
                cov='measurement_mean_coverage',
                perc_10='measurement_percentage10',
                perc_15='measurement_percentage15',
                perc_20='measurement_percentage20',
                perc_30='measurement_percentage30',
                perc_50='measurement_percentage50',
                perc_100='measurement_percentage100',
            )
        )
        for exon_measurement in sample.exon_measurements:
            exon_measurement_file.write(
                '{chr}\t{start}\t{end}\t{cov}\t{perc_10}\t{perc_15}\t{perc_20}\t{perc_30}\t{perc_50}\t{perc_100}\n'.format(
                    chr=exon_measurement.exon.chr,
                    start=exon_measurement.exon.start,
                    end=exon_measurement.exon.end,
                    cov=exon_measurement.measurement_mean_coverage,
                    perc_10=exon_measurement.measurement_percentage10,
                    perc_15=exon_measurement.measurement_percentage15,
                    perc_20=exon_measurement.measurement_percentage20,
                    perc_30=exon_measurement.measurement_percentage30,
                    perc_50=exon_measurement.measurement_percentage50,
                    perc_100=exon_measurement.measurement_percentage100,
                )
            )
        exon_measurement_file.close()

        os.system('{bgzip} {file}'.format(bgzip=bgzip_path, file=exon_measurement_file_path))
        os.system('{tabix} -s 1 -b 2 -e 3 -c \'#\' {file}.gz'.format(tabix=tabix_path, file=exon_measurement_file_path))
        os.system('rsync {0}* {1}'.format(exon_measurement_file_path, EXON_MEASUREMENTS_RSYNC_PATH))
        
        # Change exon_measurement_file to path on server.
        sample.exon_measurement_file = '{0}/{1}.gz'.format(
            EXON_MEASUREMENTS_RSYNC_PATH.split(':')[-1],
            sample.exon_measurement_file
        )
        db.session.add(sample)
        db.session.commit()
